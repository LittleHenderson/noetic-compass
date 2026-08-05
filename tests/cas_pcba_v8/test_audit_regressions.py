from __future__ import annotations

from dataclasses import replace
from decimal import Decimal, localcontext
import json
from pathlib import Path
import sys
import unittest
import unicodedata


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from cas_pcba_v8 import (  # noqa: E402
    Board,
    CalibrationRef,
    ComponentInstance,
    DiagnosticCode,
    Endpoint,
    FeedbackLoop,
    InputSample,
    MeasurementKind,
    MixedSimplexAddress,
    Net,
    PortDirection,
    PortSpec,
    ProjectorProfile,
    SignalKind,
    SimulationError,
    Unit,
    build_reachable_fuse_board,
    build_valid_guard_board,
    exact_decimal_sum,
    fisher_rao_distance,
    projector_overlap,
    simulate,
    validate_board,
)
from cas_pcba_v8.geometry import GeometryError  # noqa: E402
from cas_pcba_v8.integrity import IntegrityError  # noqa: E402
from cas_pcba_v8.values import (  # noqa: E402
    canonical_value_text,
    value_text_sha256,
)


def _under_precision(precision: int, function):
    with localcontext() as context:
        context.prec = precision
        return function()


def _scale_board() -> Board:
    return Board(
        "decimal-context-board",
        "v1",
        (
            PortSpec(
                "input",
                PortDirection.INPUT,
                SignalKind.ACTIVATION,
                Unit.ACTIVATION_0_1,
            ),
            PortSpec(
                "output",
                PortDirection.OUTPUT,
                SignalKind.ACTIVATION,
                Unit.ACTIVATION_0_1,
            ),
        ),
        (
            ComponentInstance(
                "scale",
                "scale",
                "pcba8.scale.v0",
                parameters={"factor": Decimal("1"), "ceiling": Decimal("1")},
            ),
        ),
        (
            Net(
                "input",
                (Endpoint.board("input"), Endpoint("scale", "input")),
            ),
            Net(
                "output",
                (Endpoint("scale", "output"), Endpoint.board("output")),
            ),
        ),
    )


def _branching_feedback_board() -> Board:
    gain_calibration = CalibrationRef(
        "gain-cal",
        "v1",
        "A" * 64,
        MeasurementKind.DESIGN_VALUE,
        Unit.NONE,
        "structural-simulator",
        "feedback-bound.v1",
        Decimal("0"),
    )
    return Board(
        "branching-feedback",
        "v1",
        (
            PortSpec(
                "select",
                PortDirection.INPUT,
                SignalKind.DECISION,
                Unit.BOOLEAN,
            ),
            PortSpec(
                "output",
                PortDirection.OUTPUT,
                SignalKind.ACTIVATION,
                Unit.ACTIVATION_0_1,
            ),
        ),
        (
            ComponentInstance(
                "delay",
                "delay",
                "pcba8.unit-delay.v0",
                parameters={"initial": Decimal("0.1")},
            ),
            ComponentInstance(
                "gain2",
                "scale",
                "pcba8.scale.v0",
                parameters={"factor": Decimal("2"), "ceiling": Decimal("1")},
            ),
            ComponentInstance(
                "gain02",
                "scale",
                "pcba8.scale.v0",
                parameters={"factor": Decimal("0.2"), "ceiling": Decimal("1")},
            ),
            ComponentInstance("choose", "mux", "pcba8.mux.v0"),
        ),
        (
            Net(
                "delayed",
                (
                    Endpoint("delay", "output"),
                    Endpoint("gain2", "input"),
                    Endpoint("gain02", "input"),
                ),
            ),
            Net(
                "amplified",
                (Endpoint("gain2", "output"), Endpoint("choose", "when_true")),
            ),
            Net(
                "attenuated",
                (Endpoint("gain02", "output"), Endpoint("choose", "when_false")),
            ),
            Net(
                "select",
                (Endpoint.board("select"), Endpoint("choose", "select")),
            ),
            Net(
                "feedback",
                (
                    Endpoint("choose", "output"),
                    Endpoint("delay", "input"),
                    Endpoint.board("output"),
                ),
            ),
        ),
        calibrations=(gain_calibration,),
        feedback_loops=(
            FeedbackLoop(
                "branching-loop",
                ("delay", "gain2", "gain02", "choose"),
                "delay",
                Decimal("0.4"),
                "gain-cal",
            ),
        ),
    )


class DecimalContextAuditTests(unittest.TestCase):
    def test_weights_one_through_forty_are_context_invariant_and_exact(self) -> None:
        addresses = [
            _under_precision(
                precision,
                lambda: MixedSimplexAddress.from_positive_weights(
                    tuple(Decimal(index) for index in range(1, 41))
                ),
            )
            for precision in (10, 28, 60)
        ]
        self.assertTrue(all(item.weights == addresses[0].weights for item in addresses))
        self.assertTrue(
            all(item.profile_sha256 == addresses[0].profile_sha256 for item in addresses)
        )
        self.assertEqual(exact_decimal_sum(addresses[0].weights), Decimal("1"))

    def test_simulation_preserves_auditor_value_at_precisions_10_28_60(self) -> None:
        expected = Decimal("0.1219326311370217952237463801")
        board = _scale_board()
        results = [
            _under_precision(
                precision,
                lambda: simulate(board, {"input": InputSample(expected)}),
            )
            for precision in (10, 28, 60)
        ]
        output_values = [
            json.loads(result.outputs[0][1][0][1])["value"]
            for result in results
        ]
        self.assertEqual(output_values, [str(expected)] * 3)
        self.assertEqual(len({result.result_sha256 for result in results}), 1)

    def test_feedback_diagnostics_are_context_invariant(self) -> None:
        board = _branching_feedback_board()
        reports = [
            _under_precision(precision, lambda: validate_board(board))
            for precision in (10, 28, 60)
        ]
        self.assertTrue(
            all(DiagnosticCode.UNSAFE_FEEDBACK_GAIN in report.codes for report in reports)
        )
        self.assertEqual(len({report.report_sha256 for report in reports}), 1)

    def test_projector_acceptance_and_identity_are_context_invariant(self) -> None:
        matrix = (
            (Decimal("1"), Decimal("0")),
            (Decimal("0"), Decimal("0")),
        )
        profiles = [
            _under_precision(
                precision,
                lambda: ProjectorProfile(
                    "context-projector",
                    matrix,
                    1,
                    basis_id="basis-a",
                    source_id="source-a",
                ),
            )
            for precision in (10, 28, 60)
        ]
        self.assertEqual(len({item.profile_sha256 for item in profiles}), 1)
        self.assertEqual(
            {
                (
                    item.symmetry_residual,
                    item.idempotence_residual,
                    item.trace_residual,
                )
                for item in profiles
            },
            {(Decimal("0"), Decimal("0"), Decimal("0"))},
        )


class ProjectorAuditTests(unittest.TestCase):
    def test_two_identity_is_rejected_even_with_auditor_tolerance_ten(self) -> None:
        with self.assertRaises(GeometryError):
            ProjectorProfile(
                "two-identity",
                ((Decimal("2"), Decimal("0")), (Decimal("0"), Decimal("2"))),
                rank=2,
                tolerance=Decimal("10"),
            )

    def test_orthogonal_same_shape_profiles_have_distinct_full_identities(self) -> None:
        left = ProjectorProfile(
            "same-label",
            ((Decimal("1"), Decimal("0")), (Decimal("0"), Decimal("0"))),
            rank=1,
            basis_id="basis-a",
            source_id="source-a",
        )
        right = ProjectorProfile(
            "same-label",
            ((Decimal("0"), Decimal("0")), (Decimal("0"), Decimal("1"))),
            rank=1,
            basis_id="basis-a",
            source_id="source-a",
        )
        self.assertNotEqual(left.matrix_sha256, right.matrix_sha256)
        self.assertNotEqual(left.profile_sha256, right.profile_sha256)
        self.assertEqual(projector_overlap(left, right), Decimal("0"))


class FisherRaoLimitationTests(unittest.TestCase):
    def test_binary64_pseudometric_can_collapse_distinct_exact_profiles(self) -> None:
        left = MixedSimplexAddress((Decimal("0.025"),) * 40)
        epsilon = Decimal("1E-100")
        weights = list(left.weights)
        weights[0] = exact_decimal_sum((weights[0], epsilon))
        weights[1] = exact_decimal_sum((weights[1], epsilon.copy_negate()))
        right = MixedSimplexAddress(tuple(weights))
        self.assertNotEqual(left.profile_sha256, right.profile_sha256)
        self.assertEqual(fisher_rao_distance(left, right), Decimal("0.0"))
        self.assertFalse(fisher_rao_distance.is_exact_metric)


class DrcSoundnessAuditTests(unittest.TestCase):
    def test_activation_boolean_pair_is_rejected_before_simulation(self) -> None:
        board = Board(
            "bad-quantity-pair",
            "v1",
            (
                PortSpec(
                    "input",
                    PortDirection.INPUT,
                    SignalKind.ACTIVATION,
                    Unit.BOOLEAN,
                ),
                PortSpec(
                    "output",
                    PortDirection.OUTPUT,
                    SignalKind.ACTIVATION,
                    Unit.BOOLEAN,
                ),
            ),
            (),
            (Net("wire", (Endpoint.board("input"), Endpoint.board("output"))),),
        )
        self.assertIn(
            DiagnosticCode.INVALID_SIGNAL_UNIT_PAIR,
            validate_board(board).codes,
        )
        with self.assertRaises(SimulationError):
            simulate(board, {"input": InputSample(Decimal("0.5"))})

    def test_unconnected_optional_input_has_defined_absent_semantics(self) -> None:
        board = Board(
            "optional-input",
            "v1",
            (
                PortSpec(
                    "optional",
                    PortDirection.INPUT,
                    SignalKind.ACTIVATION,
                    Unit.ACTIVATION_0_1,
                    required=False,
                ),
            ),
            (),
            (),
        )
        self.assertTrue(validate_board(board).is_clean)
        self.assertEqual(simulate(board, {}).outputs, ((0, ()),))

    def test_beta_zero_makes_reachable_fixture_fuse_unreachable(self) -> None:
        board = build_reachable_fuse_board()
        cjt = board.components[0]
        zero_beta = replace(
            cjt,
            parameters={**cjt.parameters, "beta": Decimal("0")},
        )
        report = validate_board(
            replace(board, components=(zero_beta,) + board.components[1:])
        )
        self.assertIn(DiagnosticCode.UNREACHABLE_SAFETY_THRESHOLD, report.codes)

    def test_branching_scc_does_not_mask_gain_two_cycle(self) -> None:
        report = validate_board(_branching_feedback_board())
        self.assertIn(DiagnosticCode.UNSAFE_FEEDBACK_GAIN, report.codes)
        self.assertTrue(
            any("gain2" in item.message and "2" in item.message for item in report.diagnostics)
        )

    def test_safety_critical_test_points_must_remain_explicitly_marked(self) -> None:
        board = build_valid_guard_board()
        unmarked = replace(
            board,
            test_points=tuple(
                replace(point, safety_critical=False) for point in board.test_points
            ),
        )
        self.assertIn(
            DiagnosticCode.SAFETY_TEST_POINT_NOT_MARKED,
            validate_board(unmarked).codes,
        )


class IdentityAndReferenceAuditTests(unittest.TestCase):
    def test_bool_and_string_true_never_share_value_identity(self) -> None:
        bool_text = canonical_value_text(True)
        string_text = canonical_value_text("true")
        self.assertNotEqual(bool_text, string_text)
        self.assertNotEqual(
            value_text_sha256(bool_text),
            value_text_sha256(string_text),
        )

    def test_control_bidi_format_and_unicode_confusables_are_rejected(self) -> None:
        dangerous = (
            "bad\nref",
            "left\u202Eright",
            "zero\u200Djoiner",
            "p\u0441ba8",
        )
        for ref in dangerous:
            with self.subTest(ref=repr(ref)), self.assertRaises(IntegrityError):
                Board(ref, "v1", (), (), ())

    def test_every_unicode_format_character_is_rejected_from_identifiers(self) -> None:
        format_characters = tuple(
            chr(codepoint)
            for codepoint in range(sys.maxunicode + 1)
            if unicodedata.category(chr(codepoint)) == "Cf"
        )
        self.assertTrue(format_characters)
        for character in format_characters:
            with self.subTest(codepoint=f"U+{ord(character):04X}"):
                with self.assertRaises(IntegrityError):
                    Board(f"left{character}right", "v1", (), (), ())


if __name__ == "__main__":
    unittest.main()
