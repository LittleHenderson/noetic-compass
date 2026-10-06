"""Executable positive and known-fault boards for DRC regression tests."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from .model import (
    Board,
    CalibrationRef,
    ComponentInstance,
    Endpoint,
    FeedbackLoop,
    Net,
    TestPoint,
)
from .types import (
    CasState,
    Domain,
    Drive,
    MeasurementKind,
    Noetic,
    PortDirection,
    PortSpec,
    Register,
    SignalKind,
    Unit,
)


DESIGN_PROFILE_SHA256 = "A" * 64


def _calibration(ref: str, unit: Unit) -> CalibrationRef:
    return CalibrationRef(
        ref=ref,
        version="pcba8-design-scale-v0",
        profile_sha256=DESIGN_PROFILE_SHA256,
        measurement_kind=MeasurementKind.DESIGN_VALUE,
        unit=unit,
        instrument_identity="reference-simulator-not-physical-instrument",
        protocol_identity="pcba8.reference-simulation.v0",
        uncertainty=Decimal("0"),
        packet_eligible=False,
    )

def _guard_states() -> dict[str, CasState]:
    return {
        "cause": CasState(
            Noetic.ABOVE_CAUSE,
            Domain.COGNITIVE,
            Drive.F2,
            Register.ANALYTICAL,
        ),
        "bias": CasState(
            Noetic.FEMALE,
            Domain.PRINCIPLED,
            Drive.F7,
            Register.TRANSCENDENT,
        ),
        "effect": CasState(
            Noetic.NEGATIVE,
            Domain.PRINCIPLED,
            Drive.F7,
            Register.TRANSCENDENT,
        ),
    }


def build_valid_guard_board() -> Board:
    """A small acyclic design model with two calibrated safety test points."""

    return Board(
        ref="pcba8-valid-guard",
        version="0.1-research",
        ports=(
            PortSpec(
                "cause",
                PortDirection.INPUT,
                SignalKind.ACTIVATION,
                Unit.ACTIVATION_0_1,
            ),
            PortSpec(
                "bias",
                PortDirection.INPUT,
                SignalKind.ACTIVATION,
                Unit.ACTIVATION_0_1,
            ),
            PortSpec(
                "decision",
                PortDirection.OUTPUT,
                SignalKind.DECISION,
                Unit.BOOLEAN,
            ),
        ),
        components=(
            ComponentInstance(
                ref="guard",
                kind="cjt",
                semantic_profile="pcba8.cjt.reference.v0",
                parameters={
                    "beta": Decimal("2"),
                    "saturation": Decimal("0.8"),
                    "cutoff": Decimal("0.1"),
                },
                state_bindings=_guard_states(),
                safety_critical=True,
            ),
            ComponentInstance(
                ref="decide",
                kind="decision_threshold",
                semantic_profile="pcba8.decision-threshold.v0",
                parameters={"threshold": Decimal("0.7")},
                safety_critical=True,
            ),
        ),
        nets=(
            Net("cause", (Endpoint.board("cause"), Endpoint("guard", "cause"))),
            Net("bias", (Endpoint.board("bias"), Endpoint("guard", "bias"))),
            Net(
                "guard-effect",
                (Endpoint("guard", "effect"), Endpoint("decide", "input")),
                safety_critical=True,
            ),
            Net(
                "decision",
                (Endpoint("decide", "decision"), Endpoint.board("decision")),
                safety_critical=True,
            ),
        ),
        test_points=(
            TestPoint("tp-guard", "guard-effect", "cal-activation", True),
            TestPoint("tp-decision", "decision", "cal-boolean", True),
        ),
        calibrations=(
            _calibration("cal-activation", Unit.ACTIVATION_0_1),
            _calibration("cal-boolean", Unit.BOOLEAN),
        ),
    )


def _fuse_board(threshold: Decimal, ref: str) -> Board:
    return Board(
        ref=ref,
        version="0.1-research",
        ports=(
            PortSpec(
                "cause",
                PortDirection.INPUT,
                SignalKind.ACTIVATION,
                Unit.ACTIVATION_0_1,
            ),
            PortSpec(
                "bias",
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
        components=(
            ComponentInstance(
                ref="red-cjt",
                kind="cjt",
                semantic_profile="pcba8.cjt.reference.v0",
                parameters={
                    "beta": Decimal("10"),
                    "saturation": Decimal("0.1"),
                    "cutoff": Decimal("0"),
                },
                state_bindings=_guard_states(),
                safety_critical=True,
            ),
            ComponentInstance(
                ref="red-fuse",
                kind="fuse",
                semantic_profile="pcba8.fuse.reference.v0",
                parameters={
                    "threshold": threshold,
                    "action": "permanent_block",
                },
                safety_critical=True,
            ),
        ),
        nets=(
            Net("cause", (Endpoint.board("cause"), Endpoint("red-cjt", "cause"))),
            Net("bias", (Endpoint.board("bias"), Endpoint("red-cjt", "bias"))),
            Net(
                "red-activation",
                (Endpoint("red-cjt", "effect"), Endpoint("red-fuse", "input")),
                safety_critical=True,
            ),
            Net(
                "fused-output",
                (Endpoint("red-fuse", "output"), Endpoint.board("output")),
                safety_critical=True,
            ),
        ),
        test_points=(
            TestPoint("tp-red", "red-activation", "cal-activation", True),
            TestPoint("tp-fuse", "fused-output", "cal-activation", True),
        ),
        calibrations=(_calibration("cal-activation", Unit.ACTIVATION_0_1),),
    )


def build_unreachable_fuse_board() -> Board:
    """Known fault transcribed from the book: sat=0.1 cannot reach fuse=0.9."""

    return _fuse_board(Decimal("0.9"), "pcba8-known-fault-unreachable-fuse")


def build_reachable_fuse_board() -> Board:
    """A reference fixture whose threshold lies within the upstream envelope."""

    return _fuse_board(Decimal("0.09"), "pcba8-reference-reachable-fuse")


def build_missing_test_point_board() -> Board:
    board = build_valid_guard_board()
    return replace(
        board,
        ref="pcba8-known-fault-missing-test-point",
        test_points=(board.test_points[1],),
    )


def build_unsafe_feedback_board() -> Board:
    """A combinational two-component cycle with no delay or declaration."""

    return Board(
        ref="pcba8-known-fault-unsafe-feedback",
        version="0.1-research",
        ports=(
            PortSpec(
                "output",
                PortDirection.OUTPUT,
                SignalKind.ACTIVATION,
                Unit.ACTIVATION_0_1,
            ),
        ),
        components=(
            ComponentInstance("a", "pass", "pcba8.pass.v0"),
            ComponentInstance("b", "pass", "pcba8.pass.v0"),
        ),
        nets=(
            Net(
                "a-to-b",
                (
                    Endpoint("a", "output"),
                    Endpoint("b", "input"),
                    Endpoint.board("output"),
                ),
            ),
            Net("b-to-a", (Endpoint("b", "output"), Endpoint("a", "input"))),
        ),
    )


def build_safe_feedback_board() -> Board:
    """A sub-unity synchronous loop whose unit delay breaks combinational flow."""

    return Board(
        ref="pcba8-safe-feedback-reference",
        version="0.1-research",
        ports=(
            PortSpec(
                "output",
                PortDirection.OUTPUT,
                SignalKind.ACTIVATION,
                Unit.ACTIVATION_0_1,
            ),
        ),
        components=(
            ComponentInstance(
                "delay",
                "delay",
                "pcba8.unit-delay.v0",
                parameters={"initial": Decimal("0.2")},
            ),
            ComponentInstance(
                "attenuator",
                "scale",
                "pcba8.scale.v0",
                parameters={"factor": Decimal("0.5"), "ceiling": Decimal("1")},
            ),
        ),
        nets=(
            Net(
                "delayed",
                (
                    Endpoint("delay", "output"),
                    Endpoint("attenuator", "input"),
                    Endpoint.board("output"),
                ),
            ),
            Net(
                "attenuated",
                (Endpoint("attenuator", "output"), Endpoint("delay", "input")),
            ),
        ),
        test_points=(TestPoint("tp-feedback", "delayed", "cal-activation"),),
        calibrations=(
            _calibration("cal-activation", Unit.ACTIVATION_0_1),
            _calibration("cal-gain", Unit.NONE),
        ),
        feedback_loops=(
            FeedbackLoop(
                ref="feedback-loop",
                component_refs=("delay", "attenuator"),
                delay_component_ref="delay",
                max_round_trip_gain=Decimal("0.5"),
                calibration_ref="cal-gain",
            ),
        ),
    )
