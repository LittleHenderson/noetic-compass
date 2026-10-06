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
    InputSample,
    MeasurementKind,
    SimulationError,
    Unit,
    build_reachable_fuse_board,
    build_safe_feedback_board,
    build_unreachable_fuse_board,
    build_valid_guard_board,
    simulate,
)
from cas_pcba_v8.values import canonical_value_text  # noqa: E402


class ReferenceSimulationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.board = build_valid_guard_board()
        self.samples = {
            "cause": InputSample(Decimal("0.5")),
            "bias": InputSample(Decimal("1")),
        }

    def test_guard_simulation_is_deterministic_and_trace_emitting(self) -> None:
        first = simulate(self.board, self.samples)
        second = simulate(self.board, self.samples)
        self.assertEqual(first.result_sha256, second.result_sha256)
        self.assertEqual(first.trace, second.trace)
        self.assertEqual(
            first.outputs,
            ((0, (("decision", canonical_value_text(True)),)),),
        )
        self.assertEqual(
            [event.subject_ref for event in first.trace],
            ["guard", "decide", "test-point:tp-decision", "test-point:tp-guard"],
        )
        self.assertEqual(first.boundary.license_status, "NOT LICENSED")

    def test_aggregation_preserves_immediate_and_transitive_children(self) -> None:
        result = simulate(self.board, self.samples)
        guard_output = next(
            record
            for record in result.measurements
            if record.producer_ref == "guard" and record.port_ref == "effect"
        )
        self.assertEqual(len(guard_output.child_measurement_ids), 2)
        roots = [result.measurement(item) for item in guard_output.child_measurement_ids]
        self.assertEqual({record.producer_ref for record in roots}, {"$board"})

        decision_probe = next(
            record
            for record in result.measurements
            if record.producer_ref == "test-point:tp-decision"
        )
        ancestry = result.ancestry(decision_probe.measurement_id)
        self.assertIn(guard_output.measurement_id, ancestry)
        for child in guard_output.child_measurement_ids:
            self.assertIn(child, ancestry)

    def test_self_attested_instrumented_roots_are_never_packet_eligible(self) -> None:
        instrumented = CalibrationRef(
            ref="instrumented-activation",
            version="instrument-v1",
            profile_sha256="C" * 64,
            measurement_kind=MeasurementKind.INSTRUMENTED,
            unit=Unit.ACTIVATION_0_1,
            instrument_identity="bench-instrument-serial-001",
            protocol_identity="calibration-protocol-v1",
            uncertainty=Decimal("0.01"),
            packet_eligible=False,
        )
        board = replace(
            self.board,
            calibrations=self.board.calibrations + (instrumented,),
        )
        samples = {
            "cause": InputSample(
                Decimal("0.5"),
                MeasurementKind.INSTRUMENTED,
                "instrumented-activation",
            ),
            "bias": InputSample(Decimal("1")),
        }
        result = simulate(board, samples)
        cause = next(
            record
            for record in result.measurements
            if record.producer_ref == "$board" and record.port_ref == "cause"
        )
        self.assertFalse(cause.packet_eligible)
        derived = [
            record
            for record in result.measurements
            if record.measurement_kind is MeasurementKind.MODEL_DERIVED
        ]
        self.assertTrue(derived)
        self.assertTrue(all(not record.packet_eligible for record in derived))
        self.assertIn(
            cause.measurement_id,
            next(
                record for record in derived if record.producer_ref == "guard"
            ).child_measurement_ids,
        )

    def test_invalid_board_never_runs(self) -> None:
        with self.assertRaisesRegex(SimulationError, "PCBA8-SAF-001"):
            simulate(
                build_unreachable_fuse_board(),
                {
                    "cause": InputSample(Decimal("1")),
                    "bias": InputSample(Decimal("1")),
                },
            )

    def test_reachable_fuse_trips_and_remains_blocked_across_ticks(self) -> None:
        result = simulate(
            build_reachable_fuse_board(),
            {
                "cause": InputSample(Decimal("1")),
                "bias": InputSample(Decimal("1")),
            },
            ticks=2,
        )
        self.assertEqual(
            result.outputs,
            (
                (0, (("output", canonical_value_text(Decimal("0"))),)),
                (1, (("output", canonical_value_text(Decimal("0"))),)),
            ),
        )
        fuse_events = [event for event in result.trace if event.subject_ref == "red-fuse"]
        self.assertEqual(len(fuse_events), 2)
        self.assertTrue(all(event.details == ("tripped=true",) for event in fuse_events))

    def test_safe_feedback_uses_one_tick_delay(self) -> None:
        result = simulate(build_safe_feedback_board(), {}, ticks=3)
        self.assertEqual(
            result.outputs,
            (
                (0, (("output", canonical_value_text(Decimal("0.2"))),)),
                (1, (("output", canonical_value_text(Decimal("0.10"))),)),
                (2, (("output", canonical_value_text(Decimal("0.050"))),)),
            ),
        )
        delayed = [event for event in result.trace if event.subject_ref == "delay"]
        self.assertEqual(
            [event.outputs[0][1] for event in delayed],
            [
                canonical_value_text(Decimal("0.2")),
                canonical_value_text(Decimal("0.10")),
                canonical_value_text(Decimal("0.050")),
            ],
        )

    def test_binary_float_input_is_rejected(self) -> None:
        samples = {"cause": InputSample(0.5), "bias": InputSample(Decimal("1"))}
        with self.assertRaises(SimulationError):
            simulate(self.board, samples)

    def test_measurement_kind_cannot_be_substituted_across_calibration_profiles(self) -> None:
        samples = {
            "cause": InputSample(
                Decimal("0.5"),
                MeasurementKind.INSTRUMENTED,
                "cal-activation",
            ),
            "bias": InputSample(Decimal("1")),
        }
        with self.assertRaisesRegex(SimulationError, "measurement kind"):
            simulate(self.board, samples)


if __name__ == "__main__":
    unittest.main()
