from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from cas_pcba_v8 import (  # noqa: E402
    Board,
    DrcReport,
    Endpoint,
    InputSample,
    MeasurementKind,
    MeasurementRecord,
    Net,
    PortDirection,
    PortSpec,
    ProjectorProfile,
    SignalKind,
    SimulationError,
    SimulationResult,
    TraceEvent,
    Unit,
    build_reachable_fuse_board,
    build_unreachable_fuse_board,
    build_valid_guard_board,
    simulate,
)
from cas_pcba_v8.boundary import fixed_research_boundary  # noqa: E402
from cas_pcba_v8.integrity import IntegrityError, sha256_payload  # noqa: E402
from cas_pcba_v8.simulation import _simulation_digest_payload  # noqa: E402
from cas_pcba_v8.values import canonical_value_text  # noqa: E402


def _guard_result(*, ticks: int = 1) -> SimulationResult:
    return simulate(
        build_valid_guard_board(),
        {
            "cause": InputSample(Decimal("0.5")),
            "bias": InputSample(Decimal("1")),
        },
        ticks=ticks,
    )


def _result_payload(
    result: SimulationResult,
    *,
    outputs: tuple[tuple[int, tuple[tuple[str, str], ...]], ...] | None = None,
    trace: tuple[TraceEvent, ...] | None = None,
    measurements: tuple[MeasurementRecord, ...] | None = None,
) -> dict[str, object]:
    return _simulation_digest_payload(
        board_ref=result.board_ref,
        board_version=result.board_version,
        board_sha256=result.board_sha256,
        source_sha256=result.source_sha256,
        catalog_sha256=result.catalog_sha256,
        engine_sha256_value=result.engine_sha256,
        decimal_context_sha256=result.decimal_context_sha256,
        drc_report_sha256=result.drc_report_sha256,
        drc_report=result.drc_report,
        drc_sha256=result.drc_sha256,
        simulator_sha256=result.simulator_sha256,
        measurement_scope_sha256=result.measurement_scope_sha256,
        ticks=result.ticks,
        outputs=outputs if outputs is not None else result.outputs,
        trace=trace if trace is not None else result.trace,
        measurements=(
            measurements if measurements is not None else result.measurements
        ),
        boundary=fixed_research_boundary(),
    )


def _reconstruct_result(
    result: SimulationResult,
    *,
    outputs: tuple[tuple[int, tuple[tuple[str, str], ...]], ...] | None = None,
    trace: tuple[TraceEvent, ...] | None = None,
    measurements: tuple[MeasurementRecord, ...] | None = None,
) -> SimulationResult:
    trace_items = trace if trace is not None else result.trace
    output_items = outputs if outputs is not None else result.outputs
    measurement_items = measurements if measurements is not None else result.measurements
    digest = sha256_payload(
        _result_payload(
            result,
            outputs=output_items,
            trace=trace_items,
            measurements=measurement_items,
        )
    )
    return SimulationResult(
        board_ref=result.board_ref,
        board_version=result.board_version,
        board_sha256=result.board_sha256,
        source_sha256=result.source_sha256,
        catalog_sha256=result.catalog_sha256,
        engine_sha256=result.engine_sha256,
        decimal_context_sha256=result.decimal_context_sha256,
        drc_report_sha256=result.drc_report_sha256,
        drc_report=result.drc_report,
        drc_sha256=result.drc_sha256,
        simulator_sha256=result.simulator_sha256,
        measurement_scope_sha256=result.measurement_scope_sha256,
        ticks=result.ticks,
        outputs=output_items,
        trace=trace_items,
        measurements=measurement_items,
        result_sha256=digest,
    )


class MeasurementConstructorAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.result = _guard_result()
        self.root = next(
            item
            for item in self.result.measurements
            if item.producer_ref == "$board" and item.port_ref == "cause"
        )
        self.derived = next(
            item for item in self.result.measurements if item.producer_ref == "guard"
        )

    def test_not_a_digest_is_rejected_by_public_constructor(self) -> None:
        with self.assertRaises(IntegrityError):
            replace(self.root, measurement_id="not-a-digest")

    def test_board_root_cannot_claim_model_derived(self) -> None:
        with self.assertRaises(SimulationError):
            MeasurementRecord.create(
                identity_scope_sha256=self.root.identity_scope_sha256,
                tick=0,
                producer_ref="$board",
                port_ref="cause",
                value_repr=self.root.value_repr,
                unit=self.root.unit,
                measurement_kind=MeasurementKind.MODEL_DERIVED,
                calibration_ref=None,
                child_measurement_ids=(),
            )

    def test_board_input_cannot_claim_derived_children(self) -> None:
        with self.assertRaisesRegex(SimulationError, "provenance roots"):
            MeasurementRecord.create(
                identity_scope_sha256=self.root.identity_scope_sha256,
                tick=0,
                producer_ref="$board",
                port_ref="cause",
                value_repr=self.root.value_repr,
                unit=self.root.unit,
                measurement_kind=MeasurementKind.DESIGN_VALUE,
                calibration_ref=None,
                child_measurement_ids=("A" * 64,),
            )

    def test_packet_eligibility_cannot_be_self_attested(self) -> None:
        with self.assertRaises(SimulationError):
            replace(self.root, packet_eligible=True)

    def test_recomputed_result_rejects_missing_child(self) -> None:
        forged = MeasurementRecord.create(
            identity_scope_sha256=self.derived.identity_scope_sha256,
            tick=self.derived.tick,
            producer_ref=self.derived.producer_ref,
            port_ref=self.derived.port_ref,
            value_repr=self.derived.value_repr,
            unit=self.derived.unit,
            measurement_kind=self.derived.measurement_kind,
            calibration_ref=self.derived.calibration_ref,
            child_measurement_ids=("A" * 64,),
        )
        measurements = tuple(
            forged if item is self.derived else item
            for item in self.result.measurements
        )
        with self.assertRaisesRegex(SimulationError, "child does not exist"):
            _reconstruct_result(self.result, measurements=measurements)

    def test_duplicate_measurement_identifiers_are_rejected(self) -> None:
        measurements = self.result.measurements + (self.root,)
        with self.assertRaisesRegex(SimulationError, "identifiers must be unique"):
            _reconstruct_result(self.result, measurements=measurements)

    def test_future_tick_dependency_is_rejected(self) -> None:
        result = _guard_result(ticks=2)
        future_root = next(
            item
            for item in result.measurements
            if item.producer_ref == "$board"
            and item.port_ref == "cause"
            and item.tick == 1
        )
        parent = next(
            item
            for item in result.measurements
            if item.producer_ref == "guard" and item.tick == 0
        )
        forged = MeasurementRecord.create(
            identity_scope_sha256=parent.identity_scope_sha256,
            tick=0,
            producer_ref=parent.producer_ref,
            port_ref=parent.port_ref,
            value_repr=parent.value_repr,
            unit=parent.unit,
            measurement_kind=parent.measurement_kind,
            calibration_ref=parent.calibration_ref,
            child_measurement_ids=(future_root.measurement_id,),
        )
        measurements = tuple(forged if item is parent else item for item in result.measurements)
        with self.assertRaisesRegex(SimulationError, "future tick"):
            _reconstruct_result(result, measurements=measurements)

    def test_trace_tick_and_producer_linkage_are_rejected(self) -> None:
        result = _guard_result(ticks=2)
        event = result.trace[0]
        wrong_tick = replace(event, tick=1)
        trace = (wrong_tick,) + result.trace[1:]
        with self.assertRaisesRegex(SimulationError, "tick linkage"):
            _reconstruct_result(result, trace=trace)

        wrong_subject = replace(event, subject_ref="other-producer")
        trace = (wrong_subject,) + result.trace[1:]
        with self.assertRaisesRegex(SimulationError, "producer linkage"):
            _reconstruct_result(result, trace=trace)

        wrong_value = replace(
            event,
            outputs=((event.outputs[0][0], canonical_value_text(Decimal("0.123"))),),
        )
        trace = (wrong_value,) + result.trace[1:]
        with self.assertRaisesRegex(SimulationError, "value linkage"):
            _reconstruct_result(result, trace=trace)

    def test_unlinked_model_derived_measurement_is_rejected(self) -> None:
        trace = tuple(
            event
            for event in self.result.trace
            if self.derived.measurement_id not in event.output_measurement_ids
        )
        trace = tuple(replace(event, sequence=index) for index, event in enumerate(trace))
        with self.assertRaisesRegex(SimulationError, "MODEL_DERIVED"):
            _reconstruct_result(self.result, trace=trace)

    def test_recomputed_result_rejects_output_not_emitted_by_net_driver(self) -> None:
        tick, values = self.result.outputs[0]
        ref, value_repr = values[0]
        payload = json.loads(value_repr)
        self.assertEqual(payload["type"], "finite")
        forged_value = canonical_value_text(not payload["finite"]["value"])
        outputs = ((tick, ((ref, forged_value),)),)
        with self.assertRaisesRegex(SimulationError, "net driver"):
            _reconstruct_result(self.result, outputs=outputs)

    def test_explicit_cycle_guard_rejects_cyclic_provenance(self) -> None:
        def forged_record(measurement_id: str, child: str) -> MeasurementRecord:
            record = object.__new__(MeasurementRecord)
            values = {
                "measurement_id": measurement_id,
                "identity_scope_sha256": self.result.measurement_scope_sha256,
                "tick": 0,
                "producer_ref": "cycle-node",
                "port_ref": "output",
                "value_repr": canonical_value_text(Decimal("0")),
                "value_sha256": sha256_payload(
                    json.loads(canonical_value_text(Decimal("0")))
                ),
                "unit": Unit.ACTIVATION_0_1,
                "measurement_kind": MeasurementKind.MODEL_DERIVED,
                "calibration_ref": None,
                "packet_eligible": False,
                "child_measurement_ids": (child,),
                "boundary": fixed_research_boundary(),
            }
            for name, value in values.items():
                object.__setattr__(record, name, value)
            return record

        first = forged_record("A" * 64, "B" * 64)
        second = forged_record("B" * 64, "A" * 64)
        with patch.object(MeasurementRecord, "revalidate", return_value=None):
            with self.assertRaisesRegex(SimulationError, "contains a cycle"):
                _reconstruct_result(self.result, measurements=(first, second))


class ReportSemanticIntegrityTests(unittest.TestCase):
    def test_empty_diagnostics_cannot_be_minted_for_an_invalid_embedded_board(self) -> None:
        with self.assertRaisesRegex(ValueError, "identity is stale or tampered"):
            DrcReport.create(
                board=build_unreachable_fuse_board(),
                diagnostics=(),
            )


class ProjectorMeasurementIdentityTests(unittest.TestCase):
    def test_full_projector_identity_distinguishes_orthogonal_inputs(self) -> None:
        board = Board(
            "projector-wire",
            "v1",
            (
                PortSpec(
                    "input",
                    PortDirection.INPUT,
                    SignalKind.PROJECTOR_PROFILE,
                    Unit.NONE,
                ),
                PortSpec(
                    "output",
                    PortDirection.OUTPUT,
                    SignalKind.PROJECTOR_PROFILE,
                    Unit.NONE,
                ),
            ),
            (),
            (Net("wire", (Endpoint.board("input"), Endpoint.board("output"))),),
        )
        left = ProjectorProfile(
            "same",
            ((Decimal("1"), Decimal("0")), (Decimal("0"), Decimal("0"))),
            1,
            basis_id="basis-a",
            source_id="source-a",
        )
        right = ProjectorProfile(
            "same",
            ((Decimal("0"), Decimal("0")), (Decimal("0"), Decimal("1"))),
            1,
            basis_id="basis-a",
            source_id="source-a",
        )
        first = simulate(board, {"input": InputSample(left)})
        second = simulate(board, {"input": InputSample(right)})
        self.assertNotEqual(first.measurements[0].value_sha256, second.measurements[0].value_sha256)
        self.assertNotEqual(first.outputs, second.outputs)
        self.assertNotEqual(first.result_sha256, second.result_sha256)
        payload = json.loads(first.measurements[0].value_repr)
        self.assertEqual(payload["matrix_sha256"], left.matrix_sha256)
        self.assertEqual(payload["profile_sha256"], left.profile_sha256)


class FuseStateScopeTests(unittest.TestCase):
    def test_fuse_latches_within_run_and_resets_between_runs(self) -> None:
        board = build_reachable_fuse_board()
        tripped = simulate(
            board,
            {
                "cause": InputSample(Decimal("1")),
                "bias": InputSample(Decimal("1")),
            },
            ticks=2,
        )
        fresh = simulate(
            board,
            {
                "cause": InputSample(Decimal("0.005")),
                "bias": InputSample(Decimal("1")),
            },
        )
        self.assertEqual(tripped.fuse_state_scope, "cas-pcba-v8.run-local-fuse-state.v1")
        self.assertEqual(
            json.loads(fresh.outputs[0][1][0][1])["value"],
            "0.050",
        )


if __name__ == "__main__":
    unittest.main()
