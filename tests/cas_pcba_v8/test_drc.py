from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from cas_pcba_v8 import (  # noqa: E402
    CalibrationRef,
    CasState,
    ComponentInstance,
    DiagnosticCode,
    Domain,
    Drive,
    Endpoint,
    MeasurementKind,
    Noetic,
    Register,
    Unit,
    build_missing_test_point_board,
    build_safe_feedback_board,
    build_unreachable_fuse_board,
    build_unsafe_feedback_board,
    build_valid_guard_board,
    validate_board,
)


class DrcFixtureTests(unittest.TestCase):
    def assertHasCode(self, board, code: DiagnosticCode) -> None:  # noqa: N802
        self.assertIn(code, validate_board(board).codes)

    def test_valid_reference_board_is_clean_and_report_is_deterministic(self) -> None:
        board = build_valid_guard_board()
        first = validate_board(board)
        second = validate_board(board)
        self.assertTrue(first.is_clean, first.to_dict())
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(first.boundary.license_status, "NOT LICENSED")

    def test_book_unreachable_fuse_fault_is_hard_error(self) -> None:
        board = build_unreachable_fuse_board()
        report = validate_board(board)
        self.assertFalse(report.is_clean)
        self.assertEqual(report.codes, (DiagnosticCode.UNREACHABLE_SAFETY_THRESHOLD,))
        self.assertIn("0.1", report.diagnostics[0].message)
        self.assertIn("0.9", report.diagnostics[0].message)

    def test_missing_safety_probe_and_undeclared_feedback_fail_closed(self) -> None:
        self.assertHasCode(
            build_missing_test_point_board(),
            DiagnosticCode.MISSING_SAFETY_TEST_POINT,
        )
        self.assertHasCode(
            build_unsafe_feedback_board(), DiagnosticCode.UNDECLARED_FEEDBACK
        )
        self.assertTrue(validate_board(build_safe_feedback_board()).is_clean)

    def test_duplicate_references_are_not_silently_overwritten(self) -> None:
        board = build_valid_guard_board()
        duplicate = replace(
            board,
            components=board.components + (board.components[0],),
        )
        self.assertHasCode(duplicate, DiagnosticCode.DUPLICATE_REFERENCE)


class DrcAdversarialTests(unittest.TestCase):
    def setUp(self) -> None:
        self.board = build_valid_guard_board()

    def codes_for_component(self, component: ComponentInstance):
        board = replace(
            self.board,
            components=(component,) + self.board.components[1:],
        )
        return validate_board(board).codes

    def test_unknown_kind_semantics_parameters_and_state_keys_are_errors(self) -> None:
        guard = self.board.components[0]
        cases = (
            (
                replace(guard, kind="book_magic_component"),
                DiagnosticCode.UNKNOWN_COMPONENT_KIND,
            ),
            (
                replace(guard, semantic_profile="unreviewed"),
                DiagnosticCode.UNRESOLVED_SEMANTICS,
            ),
            (
                replace(guard, parameters={**guard.parameters, "mystery": Decimal("1")}),
                DiagnosticCode.UNKNOWN_PARAMETER,
            ),
            (
                replace(guard, parameters={"beta": Decimal("2")}),
                DiagnosticCode.MISSING_PARAMETER,
            ),
            (
                replace(
                    guard,
                    state_bindings={
                        **guard.state_bindings,
                        "substrate_alias": guard.state_bindings["bias"],
                    },
                ),
                DiagnosticCode.UNKNOWN_STATE_BINDING,
            ),
        )
        for component, expected in cases:
            with self.subTest(code=expected.value):
                self.assertIn(expected, self.codes_for_component(component))

    def test_binary_float_and_nonfinite_parameters_are_rejected(self) -> None:
        guard = self.board.components[0]
        for beta in (2.0, Decimal("Infinity"), Decimal("NaN")):
            with self.subTest(beta=beta):
                component = replace(
                    guard,
                    parameters={**guard.parameters, "beta": beta},
                )
                self.assertIn(
                    DiagnosticCode.INVALID_PARAMETER,
                    self.codes_for_component(component),
                )

    def test_bias_must_be_at_or_above_cause_domain(self) -> None:
        guard = self.board.components[0]
        bad_bias = CasState(
            Noetic.FEMALE,
            Domain.OPERATIONAL,
            Drive.F7,
            Register.TRANSCENDENT,
        )
        component = replace(
            guard,
            state_bindings={**guard.state_bindings, "bias": bad_bias},
        )
        self.assertIn(DiagnosticCode.BIAS_INCOHERENT, self.codes_for_component(component))

    def test_unknown_endpoint_and_unit_mismatch_are_hard_errors(self) -> None:
        unknown_net = replace(
            self.board.nets[0],
            endpoints=(Endpoint.board("cause"), Endpoint("ghost", "cause")),
        )
        unknown_board = replace(
            self.board,
            nets=(unknown_net,) + self.board.nets[1:],
        )
        self.assertIn(
            DiagnosticCode.UNKNOWN_ENDPOINT_OWNER,
            validate_board(unknown_board).codes,
        )

        bad_output = replace(
            self.board.ports[-1], unit=Unit.ACTIVATION_0_1
        )
        unit_board = replace(
            self.board,
            ports=self.board.ports[:-1] + (bad_output,),
        )
        self.assertIn(DiagnosticCode.UNIT_MISMATCH, validate_board(unit_board).codes)

    def test_test_points_require_known_unit_matching_calibrations(self) -> None:
        no_cal = replace(
            self.board,
            test_points=(replace(self.board.test_points[0], calibration_ref=None),)
            + self.board.test_points[1:],
        )
        self.assertIn(
            DiagnosticCode.MISSING_TEST_POINT_CALIBRATION,
            validate_board(no_cal).codes,
        )

        mismatch = CalibrationRef(
            ref="wrong-unit",
            version="v0",
            profile_sha256="B" * 64,
            measurement_kind=MeasurementKind.DESIGN_VALUE,
            unit=Unit.VOLT,
            instrument_identity="design-only",
            protocol_identity="test",
            uncertainty=Decimal("0"),
        )
        mismatch_board = replace(
            self.board,
            calibrations=self.board.calibrations + (mismatch,),
            test_points=(replace(self.board.test_points[0], calibration_ref="wrong-unit"),)
            + self.board.test_points[1:],
        )
        self.assertIn(
            DiagnosticCode.CALIBRATION_UNIT_MISMATCH,
            validate_board(mismatch_board).codes,
        )

        untyped = replace(
            self.board.calibrations[0],
            measurement_kind="DESIGN_VALUE",  # type: ignore[arg-type]
            unit="ACTIVATION_0_1",  # type: ignore[arg-type]
        )
        untyped_board = replace(
            self.board,
            calibrations=(untyped,) + self.board.calibrations[1:],
        )
        self.assertIn(
            DiagnosticCode.INVALID_CALIBRATION,
            validate_board(untyped_board).codes,
        )

    def test_feedback_gain_one_is_rejected(self) -> None:
        board = build_safe_feedback_board()
        loop = replace(board.feedback_loops[0], max_round_trip_gain=Decimal("1"))
        report = validate_board(replace(board, feedback_loops=(loop,)))
        self.assertIn(DiagnosticCode.UNSAFE_FEEDBACK_GAIN, report.codes)

    def test_declared_feedback_bound_cannot_hide_actual_amplification(self) -> None:
        board = build_safe_feedback_board()
        attenuator = board.components[1]
        amplifying = replace(
            attenuator,
            parameters={"factor": Decimal("2"), "ceiling": Decimal("1")},
        )
        report = validate_board(
            replace(board, components=(board.components[0], amplifying))
        )
        self.assertIn(DiagnosticCode.UNSAFE_FEEDBACK_GAIN, report.codes)

    def test_safety_fuse_warn_action_is_rejected(self) -> None:
        board = build_unreachable_fuse_board()
        fuse = board.components[1]
        fuse = replace(
            fuse,
            parameters={**fuse.parameters, "action": "warn"},
        )
        report = validate_board(replace(board, components=(board.components[0], fuse)))
        self.assertIn(DiagnosticCode.UNSAFE_FUSE_ACTION, report.codes)

    def test_catalog_codes_are_unique(self) -> None:
        values = [item.value for item in DiagnosticCode]
        self.assertEqual(len(values), len(set(values)))

    def test_closed_component_catalog_cannot_be_overridden(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot be overridden"):
            validate_board(self.board, catalog={})


if __name__ == "__main__":
    unittest.main()
