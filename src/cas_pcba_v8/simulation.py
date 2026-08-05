"""Deterministic, identity-bound PCBA v8 reference simulation.

The equations are versioned design semantics, not measured model behavior.
Fuse state is run-local: it is initialized at :func:`simulate` entry, persists
only across ticks in that result, and resets on every new call.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Mapping

from .arithmetic import DECIMAL_CONTEXT_SHA256, deterministic_decimal
from .boundary import (
    ResearchBoundary,
    fixed_research_boundary,
    require_research_boundary,
)
from .contracts import DEFAULT_COMPONENT_CATALOG, ComponentContract
from .drc import validate_board
from .diagnostics import DrcReport
from .finite_values import FiniteValueError, finite_value_key
from .geometry import MixedSimplexAddress, ProjectorProfile
from .integrity import (
    SIMULATOR_PROFILE,
    engine_sha256,
    package_source_sha256,
    require_safe_reference,
    require_sha256,
    sha256_payload,
)
from .model import BOARD_ENDPOINT, Board, ComponentInstance, Endpoint
from .types import (
    CasState,
    MeasurementKind,
    PortDirection,
    PortSpec,
    SignalKind,
    Unit,
    canonical_signal_unit,
)
from .values import (
    canonical_value_text,
    validate_value_text_for_port,
    value_text_sha256,
)


FUSE_STATE_SCOPE = "cas-pcba-v8.run-local-fuse-state.v1"
MEASUREMENT_PROFILE = "cas-pcba-v8.measurement-record.v2"
TRACE_PROFILE = "cas-pcba-v8.trace-event.v2"
RESULT_PROFILE = "cas-pcba-v8.simulation-result.v2"


class SimulationError(RuntimeError):
    """Raised when a board, sample, or artifact cannot enter simulation."""


def _require_internal_reference(value: object, field_name: str) -> str:
    if type(value) is str and value == BOARD_ENDPOINT:
        return BOARD_ENDPOINT
    if type(value) is str and value.startswith("test-point:"):
        suffix = value.removeprefix("test-point:")
        require_safe_reference(suffix, field_name)
        return value
    return require_safe_reference(value, field_name)


@dataclass(frozen=True, slots=True)
class InputSample:
    value: object
    measurement_kind: MeasurementKind = MeasurementKind.DESIGN_VALUE
    calibration_ref: str | None = None

    def __post_init__(self) -> None:
        if type(self) is not InputSample:
            raise SimulationError("InputSample subclasses are not accepted")
        self.revalidate()

    def revalidate(self) -> None:
        if type(self) is not InputSample:
            raise SimulationError("input samples must use the exact type")
        if type(self.measurement_kind) is not MeasurementKind:
            raise SimulationError("InputSample.measurement_kind must be typed")
        if self.measurement_kind is MeasurementKind.MODEL_DERIVED:
            raise SimulationError("board inputs cannot claim MODEL_DERIVED provenance")
        if self.calibration_ref is not None:
            require_safe_reference(
                self.calibration_ref,
                "InputSample.calibration_ref",
            )


def _measurement_payload(
    *,
    identity_scope_sha256: str,
    tick: int,
    producer_ref: str,
    port_ref: str,
    value_repr: str,
    value_sha256: str,
    unit: Unit,
    measurement_kind: MeasurementKind,
    calibration_ref: str | None,
    packet_eligible: bool,
    child_measurement_ids: tuple[str, ...],
) -> dict[str, object]:
    return {
        "profile": MEASUREMENT_PROFILE,
        "identity_scope_sha256": identity_scope_sha256,
        "tick": tick,
        "producer_ref": producer_ref,
        "port_ref": port_ref,
        "value_repr": value_repr,
        "value_sha256": value_sha256,
        "unit": unit.value,
        "measurement_kind": measurement_kind.value,
        "calibration_ref": calibration_ref,
        "packet_eligible": packet_eligible,
        "child_measurement_ids": list(child_measurement_ids),
        "boundary": fixed_research_boundary().to_dict(),
    }


@dataclass(frozen=True, slots=True)
class MeasurementRecord:
    measurement_id: str
    identity_scope_sha256: str
    tick: int
    producer_ref: str
    port_ref: str
    value_repr: str
    value_sha256: str
    unit: Unit
    measurement_kind: MeasurementKind
    calibration_ref: str | None
    packet_eligible: bool
    child_measurement_ids: tuple[str, ...]
    boundary: ResearchBoundary = field(default_factory=fixed_research_boundary)

    def __post_init__(self) -> None:
        if type(self) is not MeasurementRecord:
            raise SimulationError("MeasurementRecord subclasses are not accepted")
        object.__setattr__(
            self,
            "child_measurement_ids",
            tuple(self.child_measurement_ids),
        )
        self.revalidate()

    @classmethod
    def create(
        cls,
        *,
        identity_scope_sha256: str,
        tick: int,
        producer_ref: str,
        port_ref: str,
        value_repr: str,
        unit: Unit,
        measurement_kind: MeasurementKind,
        calibration_ref: str | None,
        child_measurement_ids: tuple[str, ...],
    ) -> "MeasurementRecord":
        if cls is not MeasurementRecord:
            raise SimulationError("MeasurementRecord subclasses are not accepted")
        value_sha = value_text_sha256(value_repr)
        children = tuple(child_measurement_ids)
        payload = _measurement_payload(
            identity_scope_sha256=identity_scope_sha256,
            tick=tick,
            producer_ref=producer_ref,
            port_ref=port_ref,
            value_repr=value_repr,
            value_sha256=value_sha,
            unit=unit,
            measurement_kind=measurement_kind,
            calibration_ref=calibration_ref,
            packet_eligible=False,
            child_measurement_ids=children,
        )
        return cls(
            measurement_id=sha256_payload(payload),
            identity_scope_sha256=identity_scope_sha256,
            tick=tick,
            producer_ref=producer_ref,
            port_ref=port_ref,
            value_repr=value_repr,
            value_sha256=value_sha,
            unit=unit,
            measurement_kind=measurement_kind,
            calibration_ref=calibration_ref,
            packet_eligible=False,
            child_measurement_ids=children,
        )

    def revalidate(self) -> None:
        if type(self) is not MeasurementRecord:
            raise SimulationError("measurements must use the exact type")
        require_research_boundary(self.boundary)
        require_sha256(self.measurement_id, "MeasurementRecord.measurement_id")
        require_sha256(
            self.identity_scope_sha256,
            "MeasurementRecord.identity_scope_sha256",
        )
        if type(self.tick) is not int or self.tick < 0:
            raise SimulationError("measurement tick must be a non-negative integer")
        _require_internal_reference(
            self.producer_ref,
            "MeasurementRecord.producer_ref",
        )
        require_safe_reference(self.port_ref, "MeasurementRecord.port_ref")
        if type(self.unit) is not Unit:
            raise SimulationError("measurement unit must be typed")
        if type(self.measurement_kind) is not MeasurementKind:
            raise SimulationError("measurement kind must be typed")
        if self.calibration_ref is not None:
            require_safe_reference(
                self.calibration_ref,
                "MeasurementRecord.calibration_ref",
            )
        if self.packet_eligible is not False:
            raise SimulationError(
                "self-attested PCBA measurements are never packet-eligible"
            )
        if self.producer_ref == BOARD_ENDPOINT:
            if self.measurement_kind is MeasurementKind.MODEL_DERIVED:
                raise SimulationError("board-input measurements cannot be model-derived")
            if self.child_measurement_ids:
                raise SimulationError("board-input measurements must be provenance roots")
        elif self.measurement_kind is not MeasurementKind.MODEL_DERIVED:
            raise SimulationError("simulated producers must emit MODEL_DERIVED records")
        actual_value_sha = value_text_sha256(self.value_repr)
        if self.value_sha256 != actual_value_sha:
            raise SimulationError("measurement value identity is stale or tampered")
        if type(self.child_measurement_ids) is not tuple:
            raise SimulationError("measurement children must use an exact tuple")
        if len(set(self.child_measurement_ids)) != len(self.child_measurement_ids):
            raise SimulationError("measurement children must be unique")
        for child in self.child_measurement_ids:
            require_sha256(child, "MeasurementRecord child")
            if child == self.measurement_id:
                raise SimulationError("a measurement cannot be its own child")
        expected = sha256_payload(
            _measurement_payload(
                identity_scope_sha256=self.identity_scope_sha256,
                tick=self.tick,
                producer_ref=self.producer_ref,
                port_ref=self.port_ref,
                value_repr=self.value_repr,
                value_sha256=self.value_sha256,
                unit=self.unit,
                measurement_kind=self.measurement_kind,
                calibration_ref=self.calibration_ref,
                packet_eligible=self.packet_eligible,
                child_measurement_ids=self.child_measurement_ids,
            )
        )
        if self.measurement_id != expected:
            raise SimulationError("measurement identity is stale or tampered")

    def to_dict(self) -> dict[str, object]:
        self.revalidate()
        return {
            "measurement_id": self.measurement_id,
            "identity_scope_sha256": self.identity_scope_sha256,
            "tick": self.tick,
            "producer_ref": self.producer_ref,
            "port_ref": self.port_ref,
            "value_repr": self.value_repr,
            "value_sha256": self.value_sha256,
            "unit": self.unit.value,
            "measurement_kind": self.measurement_kind.value,
            "calibration_ref": self.calibration_ref,
            "packet_eligible": self.packet_eligible,
            "child_measurement_ids": list(self.child_measurement_ids),
            "boundary": self.boundary.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class TraceEvent:
    sequence: int
    tick: int
    subject_ref: str
    semantic_profile: str
    inputs: tuple[tuple[str, str], ...]
    outputs: tuple[tuple[str, str], ...]
    output_measurement_ids: tuple[str, ...]
    details: tuple[str, ...] = ()
    boundary: ResearchBoundary = field(default_factory=fixed_research_boundary)

    def __post_init__(self) -> None:
        if type(self) is not TraceEvent:
            raise SimulationError("TraceEvent subclasses are not accepted")
        object.__setattr__(self, "inputs", tuple(tuple(item) for item in self.inputs))
        object.__setattr__(self, "outputs", tuple(tuple(item) for item in self.outputs))
        object.__setattr__(
            self,
            "output_measurement_ids",
            tuple(self.output_measurement_ids),
        )
        object.__setattr__(self, "details", tuple(self.details))
        self.revalidate()

    def revalidate(self) -> None:
        if type(self) is not TraceEvent:
            raise SimulationError("trace events must use the exact type")
        require_research_boundary(self.boundary)
        if type(self.sequence) is not int or self.sequence < 0:
            raise SimulationError("trace sequence must be a non-negative integer")
        if type(self.tick) is not int or self.tick < 0:
            raise SimulationError("trace tick must be a non-negative integer")
        _require_internal_reference(self.subject_ref, "TraceEvent.subject_ref")
        require_safe_reference(
            self.semantic_profile,
            "TraceEvent.semantic_profile",
        )
        for field_name, values in (("inputs", self.inputs), ("outputs", self.outputs)):
            if type(values) is not tuple or any(
                type(item) is not tuple
                or len(item) != 2
                or type(item[0]) is not str
                or type(item[1]) is not str
                for item in values
            ):
                raise SimulationError(f"trace {field_name} must contain exact string pairs")
            refs: list[str] = []
            for ref, value_text in values:
                require_safe_reference(ref, f"TraceEvent.{field_name} ref")
                value_text_sha256(value_text)
                refs.append(ref)
            if len(refs) != len(set(refs)):
                raise SimulationError(f"trace {field_name} refs must be unique")
        if type(self.output_measurement_ids) is not tuple or any(
            type(item) is not str for item in self.output_measurement_ids
        ):
            raise SimulationError("trace measurement links must be exact strings")
        if len(set(self.output_measurement_ids)) != len(self.output_measurement_ids):
            raise SimulationError("trace measurement links must be unique")
        for measurement_id in self.output_measurement_ids:
            require_sha256(measurement_id, "TraceEvent output measurement")
        if type(self.details) is not tuple or any(type(item) is not str for item in self.details):
            raise SimulationError("trace details must be strings")

    def to_dict(self) -> dict[str, object]:
        self.revalidate()
        return {
            "sequence": self.sequence,
            "tick": self.tick,
            "subject_ref": self.subject_ref,
            "semantic_profile": self.semantic_profile,
            "inputs": [list(item) for item in self.inputs],
            "outputs": [list(item) for item in self.outputs],
            "output_measurement_ids": list(self.output_measurement_ids),
            "details": list(self.details),
            "boundary": self.boundary.to_dict(),
        }


def _simulator_sha256(
    *,
    source_sha256: str,
    engine_sha256_value: str,
    catalog_sha256: str,
    drc_sha256: str,
) -> str:
    return sha256_payload(
        {
            "profile": SIMULATOR_PROFILE,
            "source_sha256": source_sha256,
            "engine_sha256": engine_sha256_value,
            "catalog_sha256": catalog_sha256,
            "decimal_context_sha256": DECIMAL_CONTEXT_SHA256,
            "drc_sha256": drc_sha256,
            "fuse_state_scope": FUSE_STATE_SCOPE,
        }
    )


def _measurement_scope_sha256(
    *,
    board_sha256: str,
    source_sha256: str,
    engine_sha256_value: str,
    catalog_sha256: str,
    drc_report_sha256: str,
    simulator_sha256: str,
) -> str:
    return sha256_payload(
        {
            "profile": "cas-pcba-v8.measurement-scope.v1",
            "board_sha256": board_sha256,
            "source_sha256": source_sha256,
            "engine_sha256": engine_sha256_value,
            "catalog_sha256": catalog_sha256,
            "decimal_context_sha256": DECIMAL_CONTEXT_SHA256,
            "drc_report_sha256": drc_report_sha256,
            "simulator_sha256": simulator_sha256,
            "boundary": fixed_research_boundary().to_dict(),
        }
    )


def _simulation_digest_payload(
    *,
    board_ref: str,
    board_version: str,
    board_sha256: str,
    source_sha256: str,
    catalog_sha256: str,
    engine_sha256_value: str,
    decimal_context_sha256: str,
    drc_report_sha256: str,
    drc_report: DrcReport,
    drc_sha256: str,
    simulator_sha256: str,
    measurement_scope_sha256: str,
    ticks: int,
    outputs: tuple[tuple[int, tuple[tuple[str, str], ...]], ...],
    trace: tuple[TraceEvent, ...],
    measurements: tuple[MeasurementRecord, ...],
    boundary: ResearchBoundary,
) -> dict[str, object]:
    return {
        "profile": RESULT_PROFILE,
        "board_ref": board_ref,
        "board_version": board_version,
        "board_sha256": board_sha256,
        "source_sha256": source_sha256,
        "catalog_sha256": catalog_sha256,
        "engine_sha256": engine_sha256_value,
        "decimal_context_sha256": decimal_context_sha256,
        "drc_report_sha256": drc_report_sha256,
        "drc_report": drc_report.to_dict(),
        "drc_sha256": drc_sha256,
        "simulator_sha256": simulator_sha256,
        "measurement_scope_sha256": measurement_scope_sha256,
        "fuse_state_scope": FUSE_STATE_SCOPE,
        "ticks": ticks,
        "outputs": [
            [tick, [list(item) for item in values]]
            for tick, values in outputs
        ],
        "trace": [item.to_dict() for item in trace],
        "measurements": [item.to_dict() for item in measurements],
        "boundary": boundary.to_dict(),
    }


@dataclass(frozen=True, slots=True)
class SimulationResult:
    board_ref: str
    board_version: str
    board_sha256: str
    source_sha256: str
    catalog_sha256: str
    engine_sha256: str
    decimal_context_sha256: str
    drc_report_sha256: str
    drc_report: DrcReport
    drc_sha256: str
    simulator_sha256: str
    measurement_scope_sha256: str
    ticks: int
    outputs: tuple[tuple[int, tuple[tuple[str, str], ...]], ...]
    trace: tuple[TraceEvent, ...]
    measurements: tuple[MeasurementRecord, ...]
    result_sha256: str
    fuse_state_scope: str = FUSE_STATE_SCOPE
    boundary: ResearchBoundary = field(default_factory=fixed_research_boundary)

    def __post_init__(self) -> None:
        if type(self) is not SimulationResult:
            raise SimulationError("SimulationResult subclasses are not accepted")
        object.__setattr__(
            self,
            "outputs",
            tuple(
                (tick, tuple(tuple(item) for item in values))
                for tick, values in self.outputs
            ),
        )
        object.__setattr__(self, "trace", tuple(self.trace))
        object.__setattr__(self, "measurements", tuple(self.measurements))
        self._require_valid()

    def verify_identity(self) -> bool:
        if type(self) is not SimulationResult:
            return False
        require_research_boundary(self.boundary)
        try:
            self._validate_structure()
        except (SimulationError, ValueError, TypeError):
            return False
        expected = sha256_payload(
            _simulation_digest_payload(
                board_ref=self.board_ref,
                board_version=self.board_version,
                board_sha256=self.board_sha256,
                source_sha256=self.source_sha256,
                catalog_sha256=self.catalog_sha256,
                engine_sha256_value=self.engine_sha256,
                decimal_context_sha256=self.decimal_context_sha256,
                drc_report_sha256=self.drc_report_sha256,
                drc_report=self.drc_report,
                drc_sha256=self.drc_sha256,
                simulator_sha256=self.simulator_sha256,
                measurement_scope_sha256=self.measurement_scope_sha256,
                ticks=self.ticks,
                outputs=self.outputs,
                trace=self.trace,
                measurements=self.measurements,
                boundary=self.boundary,
            )
        )
        return self.result_sha256 == expected

    def _require_valid(self) -> None:
        if type(self) is not SimulationResult:
            raise SimulationError("simulation results must use the exact type")
        require_research_boundary(self.boundary)
        try:
            self._validate_structure()
        except SimulationError:
            raise
        except (TypeError, ValueError) as exc:
            raise SimulationError(
                "simulation result structure is stale or tampered"
            ) from exc
        expected = sha256_payload(
            _simulation_digest_payload(
                board_ref=self.board_ref,
                board_version=self.board_version,
                board_sha256=self.board_sha256,
                source_sha256=self.source_sha256,
                catalog_sha256=self.catalog_sha256,
                engine_sha256_value=self.engine_sha256,
                decimal_context_sha256=self.decimal_context_sha256,
                drc_report_sha256=self.drc_report_sha256,
                drc_report=self.drc_report,
                drc_sha256=self.drc_sha256,
                simulator_sha256=self.simulator_sha256,
                measurement_scope_sha256=self.measurement_scope_sha256,
                ticks=self.ticks,
                outputs=self.outputs,
                trace=self.trace,
                measurements=self.measurements,
                boundary=self.boundary,
            )
        )
        if self.result_sha256 != expected:
            raise SimulationError("simulation result identity is stale or tampered")

    def _validate_structure(self) -> None:
        require_safe_reference(self.board_ref, "SimulationResult.board_ref")
        require_safe_reference(self.board_version, "SimulationResult.board_version")
        for field_name in (
            "board_sha256",
            "source_sha256",
            "catalog_sha256",
            "engine_sha256",
            "decimal_context_sha256",
            "drc_report_sha256",
            "drc_sha256",
            "simulator_sha256",
            "measurement_scope_sha256",
            "result_sha256",
        ):
            require_sha256(getattr(self, field_name), f"SimulationResult.{field_name}")
        if type(self.fuse_state_scope) is not str or self.fuse_state_scope != FUSE_STATE_SCOPE:
            raise SimulationError("fuse state scope is stale or unsupported")
        if type(self.ticks) is not int or self.ticks <= 0:
            raise SimulationError("result ticks must be a positive integer")
        if type(self.drc_report) is not DrcReport:
            raise SimulationError("result must embed its exact typed DRC report")
        if not self.drc_report.is_clean:
            raise SimulationError("result DRC report must be clean")
        if (
            self.drc_report.report_sha256 != self.drc_report_sha256
            or self.drc_report.board_ref != self.board_ref
            or self.drc_report.board_sha256 != self.board_sha256
            or self.drc_report.source_sha256 != self.source_sha256
            or self.drc_report.catalog_sha256 != self.catalog_sha256
            or self.drc_report.engine_sha256 != self.engine_sha256
            or self.drc_report.decimal_context_sha256
            != self.decimal_context_sha256
            or self.drc_report.drc_sha256 != self.drc_sha256
            or self.drc_report.board.version != self.board_version
        ):
            raise SimulationError("embedded DRC report linkage is inconsistent")
        board = self.drc_report.board
        board.revalidate()

        from .contracts import component_catalog_sha256

        current_source = package_source_sha256()
        current_catalog = component_catalog_sha256()
        current_engine = engine_sha256(catalog_sha256=current_catalog)
        current_simulator = _simulator_sha256(
            source_sha256=current_source,
            engine_sha256_value=current_engine,
            catalog_sha256=current_catalog,
            drc_sha256=self.drc_sha256,
        )
        expected_scope = _measurement_scope_sha256(
            board_sha256=self.board_sha256,
            source_sha256=self.source_sha256,
            engine_sha256_value=self.engine_sha256,
            catalog_sha256=self.catalog_sha256,
            drc_report_sha256=self.drc_report_sha256,
            simulator_sha256=self.simulator_sha256,
        )
        if (
            self.source_sha256 != current_source
            or self.catalog_sha256 != current_catalog
            or self.engine_sha256 != current_engine
            or self.decimal_context_sha256 != DECIMAL_CONTEXT_SHA256
            or self.simulator_sha256 != current_simulator
            or self.measurement_scope_sha256 != expected_scope
        ):
            raise SimulationError("runtime identity binding is stale or tampered")

        if (
            type(self.outputs) is not tuple
            or type(self.trace) is not tuple
            or type(self.measurements) is not tuple
            or any(
                type(item) is not tuple
                or len(item) != 2
                or type(item[0]) is not int
                or type(item[1]) is not tuple
                for item in self.outputs
            )
        ):
            raise SimulationError("result collections must use exact tuple structure")
        output_ticks = tuple(tick for tick, _ in self.outputs)
        if output_ticks != tuple(range(self.ticks)):
            raise SimulationError("result outputs must contain each tick exactly once")
        for _, values in self.outputs:
            if type(values) is not tuple or any(
                type(item) is not tuple
                or len(item) != 2
                or type(item[0]) is not str
                or type(item[1]) is not str
                for item in values
            ):
                raise SimulationError("result outputs must contain exact string pairs")
            refs = [ref for ref, _ in values]
            if refs != sorted(refs) or len(refs) != len(set(refs)):
                raise SimulationError("result output refs must be sorted and unique")
            for ref, value_text in values:
                require_safe_reference(ref, "SimulationResult output ref")
                value_text_sha256(value_text)

        records: dict[str, MeasurementRecord] = {}
        records_by_coordinate: dict[tuple[int, str, str], MeasurementRecord] = {}
        duplicate_coordinate = False
        for record in self.measurements:
            if type(record) is not MeasurementRecord:
                raise SimulationError("result measurements must be typed")
            record.revalidate()
            if record.identity_scope_sha256 != self.measurement_scope_sha256:
                raise SimulationError("measurement scope does not match its result")
            if record.tick >= self.ticks:
                raise SimulationError("measurement tick lies outside the result")
            if record.measurement_id in records:
                raise SimulationError("measurement identifiers must be unique")
            records[record.measurement_id] = record
            coordinate = (record.tick, record.producer_ref, record.port_ref)
            if coordinate in records_by_coordinate:
                duplicate_coordinate = True
            records_by_coordinate[coordinate] = record

        for record in self.measurements:
            for child_id in record.child_measurement_ids:
                child = records.get(child_id)
                if child is None:
                    raise SimulationError("measurement child does not exist")
                if child.tick > record.tick:
                    raise SimulationError("measurement cannot depend on a future tick")

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(measurement_id: str) -> None:
            if measurement_id in visiting:
                raise SimulationError("measurement provenance graph contains a cycle")
            if measurement_id in visited:
                return
            visiting.add(measurement_id)
            for child_id in records[measurement_id].child_measurement_ids:
                visit(child_id)
            visiting.remove(measurement_id)
            visited.add(measurement_id)

        for measurement_id in sorted(records):
            visit(measurement_id)
        if duplicate_coordinate:
            raise SimulationError("measurement producer coordinates must be unique")

        board_ports = {port.ref: port for port in board.ports}
        components = {component.ref: component for component in board.components}
        calibrations = {item.ref: item for item in board.calibrations}
        points = {point.ref: point for point in board.test_points}
        contracts = {
            ref: DEFAULT_COMPONENT_CATALOG[component.kind]
            for ref, component in components.items()
        }
        endpoint_nets: dict[Endpoint, str] = {}
        endpoint_ports: dict[Endpoint, PortSpec] = {}
        net_drivers: dict[str, Endpoint] = {}
        for net in board.nets:
            for endpoint in net.endpoints:
                endpoint_nets[endpoint] = net.ref
                if endpoint.owner_ref == BOARD_ENDPOINT:
                    port = board_ports[endpoint.port_ref]
                else:
                    port = contracts[endpoint.owner_ref].port(endpoint.port_ref)
                    assert port is not None
                endpoint_ports[endpoint] = port
                if port.direction is PortDirection.INPUT and endpoint.owner_ref == BOARD_ENDPOINT:
                    net_drivers[net.ref] = endpoint
                elif (
                    port.direction is PortDirection.OUTPUT
                    and endpoint.owner_ref != BOARD_ENDPOINT
                ):
                    net_drivers[net.ref] = endpoint

        expected_coordinates: set[tuple[int, str, str]] = set()
        connected_inputs = tuple(
            port
            for port in board.ports
            if port.direction is PortDirection.INPUT
            and Endpoint.board(port.ref) in endpoint_nets
        )
        for tick in range(self.ticks):
            expected_coordinates.update(
                (tick, BOARD_ENDPOINT, port.ref) for port in connected_inputs
            )
            for component in board.components:
                contract = contracts[component.ref]
                expected_coordinates.update(
                    (tick, component.ref, port.ref)
                    for port in contract.ports
                    if port.direction is PortDirection.OUTPUT
                )
            expected_coordinates.update(
                (tick, f"test-point:{point.ref}", point.net_ref)
                for point in board.test_points
            )
        if set(records_by_coordinate) != expected_coordinates:
            raise SimulationError(
                "measurements must exactly cover board inputs, component outputs, "
                "and test points at every tick"
            )

        def driver_record(net_ref: str, tick: int) -> MeasurementRecord:
            endpoint = net_drivers[net_ref]
            return records_by_coordinate[
                (tick, endpoint.owner_ref, endpoint.port_ref)
            ]

        for record in self.measurements:
            if record.producer_ref == BOARD_ENDPOINT:
                port = board_ports.get(record.port_ref)
                if (
                    port is None
                    or port.direction is not PortDirection.INPUT
                    or Endpoint.board(port.ref) not in endpoint_nets
                    or record.unit is not port.unit
                    or record.child_measurement_ids
                ):
                    raise SimulationError("board-input measurement semantics are inconsistent")
                validate_value_text_for_port(record.value_repr, port)
                calibration = (
                    calibrations.get(record.calibration_ref)
                    if record.calibration_ref is not None
                    else None
                )
                if record.calibration_ref is not None and calibration is None:
                    raise SimulationError("measurement names an unknown calibration")
                if calibration is not None and (
                    calibration.unit is not record.unit
                    or calibration.measurement_kind is not record.measurement_kind
                ):
                    raise SimulationError("measurement calibration linkage is inconsistent")
                if (
                    record.measurement_kind is MeasurementKind.INSTRUMENTED
                    and calibration is None
                ):
                    raise SimulationError("instrumented root lacks calibration evidence")
                continue

            if record.producer_ref.startswith("test-point:"):
                point_ref = record.producer_ref.removeprefix("test-point:")
                point = points.get(point_ref)
                calibration = (
                    calibrations.get(point.calibration_ref)
                    if point is not None and point.calibration_ref is not None
                    else None
                )
                if (
                    point is None
                    or calibration is None
                    or record.port_ref != point.net_ref
                    or record.unit is not calibration.unit
                    or record.calibration_ref != point.calibration_ref
                    or record.measurement_kind is not MeasurementKind.MODEL_DERIVED
                ):
                    raise SimulationError("test-point measurement semantics are inconsistent")
                validate_value_text_for_port(
                    record.value_repr,
                    endpoint_ports[net_drivers[point.net_ref]],
                )
                expected_children = (
                    driver_record(point.net_ref, record.tick).measurement_id,
                )
            else:
                component = components.get(record.producer_ref)
                if component is None:
                    raise SimulationError("measurement producer is not on the embedded board")
                contract = contracts[component.ref]
                port = contract.port(record.port_ref)
                if (
                    port is None
                    or port.direction is not PortDirection.OUTPUT
                    or record.unit is not port.unit
                    or record.calibration_ref is not None
                    or record.measurement_kind is not MeasurementKind.MODEL_DERIVED
                ):
                    raise SimulationError("component measurement semantics are inconsistent")
                validate_value_text_for_port(record.value_repr, port)
                if component.kind == "delay":
                    if record.tick == 0:
                        expected_children = ()
                    else:
                        input_net = endpoint_nets[Endpoint(component.ref, "input")]
                        expected_children = (
                            driver_record(input_net, record.tick - 1).measurement_id,
                        )
                else:
                    expected_children = tuple(
                        driver_record(
                            endpoint_nets[Endpoint(component.ref, input_port.ref)],
                            record.tick,
                        ).measurement_id
                        for input_port in contract.ports
                        if input_port.direction is PortDirection.INPUT
                    )
            if record.child_measurement_ids != expected_children:
                raise SimulationError("measurement provenance does not match board wiring")

        if tuple(event.sequence for event in self.trace) != tuple(range(len(self.trace))):
            raise SimulationError("trace sequences must be contiguous and unique")
        linked_ids: list[str] = []
        trace_subjects: dict[int, set[str]] = {
            tick: set() for tick in range(self.ticks)
        }
        for event in self.trace:
            if type(event) is not TraceEvent:
                raise SimulationError("result trace events must be typed")
            event.revalidate()
            if event.tick >= self.ticks:
                raise SimulationError("trace event tick lies outside the result")
            if event.subject_ref in trace_subjects[event.tick]:
                raise SimulationError("trace subjects must be unique within each tick")
            trace_subjects[event.tick].add(event.subject_ref)
            for measurement_id in event.output_measurement_ids:
                record = records.get(measurement_id)
                if record is None:
                    raise SimulationError("trace links to a missing measurement")
                if record.tick != event.tick:
                    raise SimulationError("trace/measurement tick linkage is inconsistent")
                if record.producer_ref != event.subject_ref:
                    raise SimulationError(
                        "trace/measurement producer linkage is inconsistent"
                    )
            if event.subject_ref.startswith("test-point:"):
                point_ref = event.subject_ref.removeprefix("test-point:")
                point = points.get(point_ref)
                if (
                    point is None
                    or event.semantic_profile != "pcba8.test-point-observation.v1"
                    or tuple(ref for ref, _ in event.inputs) != ("net",)
                    or tuple(ref for ref, _ in event.outputs) != (point.net_ref,)
                ):
                    raise SimulationError("trace test-point semantics are inconsistent")
            else:
                component = components.get(event.subject_ref)
                if component is None:
                    raise SimulationError("trace subject is not on the embedded board")
                contract = contracts[component.ref]
                expected_inputs = (
                    ()
                    if component.kind == "delay"
                    else tuple(
                        port.ref
                        for port in contract.ports
                        if port.direction is PortDirection.INPUT
                    )
                )
                expected_outputs = tuple(
                    port.ref
                    for port in contract.ports
                    if port.direction is PortDirection.OUTPUT
                )
                if (
                    event.semantic_profile != component.semantic_profile
                    or tuple(ref for ref, _ in event.inputs) != expected_inputs
                    or tuple(ref for ref, _ in event.outputs) != expected_outputs
                ):
                    raise SimulationError("trace component semantics are inconsistent")
            if len(event.outputs) != len(event.output_measurement_ids):
                raise SimulationError("trace outputs require one exact measurement link")
            for (port_ref, value_repr), measurement_id in zip(
                event.outputs,
                event.output_measurement_ids,
            ):
                record = records.get(measurement_id)
                if record is None:
                    raise SimulationError("trace links to a missing measurement")
                if record.tick != event.tick:
                    raise SimulationError("trace/measurement tick linkage is inconsistent")
                if record.producer_ref != event.subject_ref:
                    raise SimulationError("trace/measurement producer linkage is inconsistent")
                if record.port_ref != port_ref or record.value_repr != value_repr:
                    raise SimulationError("trace/measurement value linkage is inconsistent")
                linked_ids.append(measurement_id)
            if event.subject_ref.startswith("test-point:"):
                child_values = (records[event.output_measurement_ids[0]].value_repr,)
                if tuple(value for _, value in event.inputs) != child_values:
                    raise SimulationError("trace input values do not match provenance")
            elif components[event.subject_ref].kind != "delay":
                output_record = records[event.output_measurement_ids[0]]
                child_values = tuple(
                    records[child_id].value_repr
                    for child_id in output_record.child_measurement_ids
                )
                if tuple(value for _, value in event.inputs) != child_values:
                    raise SimulationError("trace input values do not match provenance")
        if len(linked_ids) != len(set(linked_ids)):
            raise SimulationError("a measurement is linked by multiple trace events")
        derived_ids = {
            record.measurement_id
            for record in self.measurements
            if record.measurement_kind is MeasurementKind.MODEL_DERIVED
        }
        if set(linked_ids) != derived_ids:
            raise SimulationError(
                "every and only MODEL_DERIVED measurement must be trace-linked"
            )
        expected_subjects = {
            *(component.ref for component in board.components),
            *(f"test-point:{point.ref}" for point in board.test_points),
        }
        if any(subjects != expected_subjects for subjects in trace_subjects.values()):
            raise SimulationError("trace must exactly cover board producers at every tick")

        expected_output_refs = tuple(
            sorted(
                port.ref
                for port in board.ports
                if port.direction is PortDirection.OUTPUT
                and Endpoint.board(port.ref) in endpoint_nets
            )
        )
        for tick, values in self.outputs:
            if tuple(ref for ref, _ in values) != expected_output_refs:
                raise SimulationError("result outputs do not match embedded board outputs")
            for ref, value_repr in values:
                net_ref = endpoint_nets[Endpoint.board(ref)]
                if driver_record(net_ref, tick).value_repr != value_repr:
                    raise SimulationError("result output value does not match its net driver")

    def measurement(self, measurement_id: str) -> MeasurementRecord:
        self._require_valid()
        require_sha256(measurement_id, "measurement_id")
        for record in self.measurements:
            if record.measurement_id == measurement_id:
                return record
        raise KeyError(measurement_id)

    def ancestry(self, measurement_id: str) -> tuple[str, ...]:
        self._require_valid()
        require_sha256(measurement_id, "measurement_id")
        result: list[str] = []
        seen: set[str] = set()
        records = {item.measurement_id: item for item in self.measurements}

        def walk(ref: str) -> None:
            for child in records[ref].child_measurement_ids:
                if child not in seen:
                    seen.add(child)
                    result.append(child)
                    walk(child)

        if measurement_id not in records:
            raise KeyError(measurement_id)
        walk(measurement_id)
        return tuple(result)


def _value_repr(value: object) -> str:
    try:
        return canonical_value_text(value)
    except ValueError as exc:
        raise SimulationError(str(exc)) from exc


def _validate_value(port: PortSpec, value: object) -> None:
    if type(port) is not PortSpec:
        raise SimulationError("value validation requires an exact PortSpec")
    port.revalidate()
    if not canonical_signal_unit(port.signal_kind, port.unit):
        raise SimulationError(
            f"port {port.ref!r} uses a noncanonical signal/unit pair"
        )
    kind = port.signal_kind
    if kind is SignalKind.ACTIVATION:
        if (
            type(value) is not Decimal
            or not value.is_finite()
            or not Decimal("0") <= value <= Decimal("1")
        ):
            raise SimulationError(
                f"port {port.ref!r} requires a finite Decimal activation in [0,1]"
            )
    elif kind is SignalKind.DECISION:
        if type(value) is not bool:
            raise SimulationError(f"port {port.ref!r} requires exact bool")
    elif kind is SignalKind.CAS_STATE:
        if type(value) is not CasState:
            raise SimulationError(f"port {port.ref!r} requires CasState")
        value.revalidate()
    elif kind is SignalKind.MIXED_SIMPLEX_ADDRESS:
        if type(value) is not MixedSimplexAddress:
            raise SimulationError(f"port {port.ref!r} requires MixedSimplexAddress")
        value.identity_payload()
    elif kind is SignalKind.PROJECTOR_PROFILE:
        if type(value) is not ProjectorProfile:
            raise SimulationError(f"port {port.ref!r} requires ProjectorProfile")
        value.revalidate()
    elif kind is SignalKind.TEXT:
        if type(value) is not str:
            raise SimulationError(f"port {port.ref!r} requires exact text")
    elif kind in (SignalKind.CLOCK, SignalKind.SCALAR):
        if type(value) is not Decimal or not value.is_finite():
            raise SimulationError(f"port {port.ref!r} requires finite Decimal")
    elif kind is SignalKind.FINITE_STATE:
        try:
            finite_value_key(value)
        except FiniteValueError as exc:
            raise SimulationError(
                f"port {port.ref!r} requires a tagged finite atom"
            ) from exc


def _endpoint_to_net(board: Board) -> dict[Endpoint, str]:
    result: dict[Endpoint, str] = {}
    for net in board.nets:
        for endpoint in net.endpoints:
            result[endpoint] = net.ref
    return result


def _driver_for_net(
    board: Board,
    contracts: Mapping[str, ComponentContract],
) -> dict[str, Endpoint]:
    board_ports = {port.ref: port for port in board.ports}
    result: dict[str, Endpoint] = {}
    for net in board.nets:
        for endpoint in net.endpoints:
            if endpoint.owner_ref == BOARD_ENDPOINT:
                port = board_ports[endpoint.port_ref]
                driver = port.direction is PortDirection.INPUT
            else:
                port = contracts[endpoint.owner_ref].port(endpoint.port_ref)
                assert port is not None
                driver = port.direction is PortDirection.OUTPUT
            if driver:
                result[net.ref] = endpoint
    return result


def _topological_non_delay_order(
    board: Board,
    contracts: Mapping[str, ComponentContract],
    drivers: Mapping[str, Endpoint],
) -> tuple[str, ...]:
    kinds = {item.ref: item.kind for item in board.components}
    nodes = {ref for ref, kind in kinds.items() if kind != "delay"}
    graph = {ref: set() for ref in nodes}
    indegree = {ref: 0 for ref in nodes}
    for net in board.nets:
        driver = drivers[net.ref]
        if driver.owner_ref == BOARD_ENDPOINT or kinds.get(driver.owner_ref) == "delay":
            continue
        for endpoint in net.endpoints:
            if endpoint.owner_ref in nodes and endpoint.owner_ref != driver.owner_ref:
                if endpoint.owner_ref not in graph[driver.owner_ref]:
                    graph[driver.owner_ref].add(endpoint.owner_ref)
                    indegree[endpoint.owner_ref] += 1
    ready = sorted(ref for ref, degree in indegree.items() if degree == 0)
    order: list[str] = []
    while ready:
        ref = ready.pop(0)
        order.append(ref)
        for target in sorted(graph[ref]):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
                ready.sort()
    if len(order) != len(nodes):
        raise SimulationError("clean DRC still contains a combinational cycle")
    return tuple(order)


def _evaluate_component(
    component: ComponentInstance,
    inputs: Mapping[str, object],
    fuse_state: dict[str, bool],
) -> tuple[dict[str, object], tuple[str, ...]]:
    details: list[str] = []
    if component.kind == "pass":
        return {"output": inputs["input"]}, ()
    if component.kind == "scale":
        source = inputs["input"]
        factor = component.parameters["factor"]
        ceiling = component.parameters["ceiling"]
        assert all(type(item) is Decimal for item in (source, factor, ceiling))
        return {
            "output": min(ceiling, max(Decimal("0"), source * factor))
        }, ()
    if component.kind == "cjt":
        cause = inputs["cause"]
        bias = inputs["bias"]
        beta = component.parameters["beta"]
        saturation = component.parameters["saturation"]
        cutoff = component.parameters["cutoff"]
        assert all(
            type(item) is Decimal
            for item in (cause, bias, beta, saturation, cutoff)
        )
        if bias <= cutoff:
            effect = Decimal("0")
            details.append("region=cutoff")
        else:
            effect = min(saturation, max(Decimal("0"), beta * cause * bias))
            details.append(
                "region=saturation" if effect == saturation else "region=active"
            )
        return {"effect": effect}, tuple(details)
    if component.kind == "decision_threshold":
        source = inputs["input"]
        threshold = component.parameters["threshold"]
        assert type(source) is Decimal and type(threshold) is Decimal
        return {"decision": source >= threshold}, ()
    if component.kind == "mux":
        select = inputs["select"]
        assert type(select) is bool
        selected = "when_true" if select else "when_false"
        return {"output": inputs[selected]}, (f"selected={selected}",)
    if component.kind == "fuse":
        source = inputs["input"]
        threshold = component.parameters["threshold"]
        action = component.parameters["action"]
        assert type(source) is Decimal and type(threshold) is Decimal
        tripped = fuse_state.get(component.ref, False)
        if not tripped and source >= threshold:
            tripped = True
            fuse_state[component.ref] = True
        output = Decimal("0") if tripped and action == "permanent_block" else source
        return {"output": output}, (f"tripped={'true' if tripped else 'false'}",)
    if component.kind == "finite_transition":
        semantics = component.finite_transition
        assert semantics is not None
        source = inputs["source"]
        source_key = finite_value_key(source)
        source_keys = tuple(finite_value_key(item) for item in semantics.source_elements)
        try:
            source_index = source_keys.index(source_key)
        except ValueError as exc:
            raise SimulationError(
                f"finite state {source!r} is outside {semantics.source_name!r}"
            ) from exc
        target_index = semantics.mapping[source_index]
        return {"target": semantics.target_elements[target_index]}, ()
    if component.kind == "delay":
        raise SimulationError("delay is evaluated by synchronous state handling")
    raise SimulationError(f"no reference semantics for component {component.kind!r}")


@deterministic_decimal
def simulate(
    board: Board,
    inputs: Mapping[str, InputSample],
    *,
    ticks: int = 1,
) -> SimulationResult:
    """Run deterministic semantics with run-local fuse/delay state."""

    require_research_boundary(fixed_research_boundary())
    if type(board) is not Board:
        raise SimulationError("simulation requires an exact Board")
    board.revalidate()
    if type(ticks) is not int or ticks <= 0:
        raise SimulationError("ticks must be a positive integer")
    if not isinstance(inputs, Mapping):
        raise SimulationError("inputs must be a mapping of exact references")
    detached_inputs: dict[str, InputSample] = {}
    for ref, sample in inputs.items():
        require_safe_reference(ref, "simulation input ref")
        detached_inputs[ref] = sample
    inputs = detached_inputs
    report = validate_board(board)
    if not report.is_clean:
        codes = ",".join(item.code.value for item in report.diagnostics)
        raise SimulationError(f"board failed PCBA8 DRC: {codes}")

    source_sha = report.source_sha256
    catalog_sha = report.catalog_sha256
    engine_sha = report.engine_sha256
    simulator_sha = _simulator_sha256(
        source_sha256=source_sha,
        engine_sha256_value=engine_sha,
        catalog_sha256=catalog_sha,
        drc_sha256=report.drc_sha256,
    )
    measurement_scope = _measurement_scope_sha256(
        board_sha256=report.board_sha256,
        source_sha256=source_sha,
        engine_sha256_value=engine_sha,
        catalog_sha256=catalog_sha,
        drc_report_sha256=report.report_sha256,
        simulator_sha256=simulator_sha,
    )

    contracts = {
        component.ref: DEFAULT_COMPONENT_CATALOG[component.kind]
        for component in board.components
    }
    components = {component.ref: component for component in board.components}
    endpoint_nets = _endpoint_to_net(board)
    board_ports = {port.ref: port for port in board.ports}
    input_ports = {
        ref: port
        for ref, port in board_ports.items()
        if port.direction is PortDirection.INPUT
        and Endpoint.board(ref) in endpoint_nets
    }
    output_ports = {
        ref: port
        for ref, port in board_ports.items()
        if port.direction is PortDirection.OUTPUT
        and Endpoint.board(ref) in endpoint_nets
    }
    if set(inputs) != set(input_ports):
        raise SimulationError(
            "input sample set must equal connected board inputs; "
            f"expected {sorted(input_ports)!r}, got {sorted(inputs)!r}"
        )
    calibrations = {item.ref: item for item in board.calibrations}
    drivers = _driver_for_net(board, contracts)
    order = _topological_non_delay_order(board, contracts, drivers)
    delay_refs = tuple(
        sorted(ref for ref, item in components.items() if item.kind == "delay")
    )

    measurements: list[MeasurementRecord] = []
    trace: list[TraceEvent] = []
    output_snapshots: list[tuple[int, tuple[tuple[str, str], ...]]] = []
    sequence = 0
    fuse_state: dict[str, bool] = {}
    delay_state: dict[str, tuple[object, str | None]] = {
        ref: (components[ref].parameters["initial"], None) for ref in delay_refs
    }

    def add_measurement(
        *,
        tick: int,
        producer_ref: str,
        port_ref: str,
        value: object,
        unit: Unit,
        kind: MeasurementKind,
        calibration_ref: str | None,
        children: tuple[str, ...],
    ) -> MeasurementRecord:
        record = MeasurementRecord.create(
            identity_scope_sha256=measurement_scope,
            tick=tick,
            producer_ref=producer_ref,
            port_ref=port_ref,
            value_repr=_value_repr(value),
            unit=unit,
            measurement_kind=kind,
            calibration_ref=calibration_ref,
            child_measurement_ids=children,
        )
        measurements.append(record)
        return record

    for tick in range(ticks):
        net_values: dict[str, object] = {}
        net_measurements: dict[str, str] = {}

        for ref in sorted(input_ports):
            port = input_ports[ref]
            sample = inputs[ref]
            if type(sample) is not InputSample:
                raise SimulationError(f"board input {ref!r} requires InputSample")
            sample.revalidate()
            _validate_value(port, sample.value)
            calibration = (
                calibrations.get(sample.calibration_ref)
                if sample.calibration_ref is not None
                else None
            )
            if sample.calibration_ref is not None and calibration is None:
                raise SimulationError(
                    f"input {ref!r} names unknown calibration {sample.calibration_ref!r}"
                )
            if calibration is not None and calibration.unit is not port.unit:
                raise SimulationError(f"input {ref!r} calibration unit mismatch")
            if (
                calibration is not None
                and calibration.measurement_kind is not sample.measurement_kind
            ):
                raise SimulationError(
                    f"input {ref!r} measurement kind does not match calibration"
                )
            if (
                sample.measurement_kind is MeasurementKind.INSTRUMENTED
                and calibration is None
            ):
                raise SimulationError(
                    f"instrumented input {ref!r} requires a calibration reference"
                )
            record = add_measurement(
                tick=tick,
                producer_ref=BOARD_ENDPOINT,
                port_ref=ref,
                value=sample.value,
                unit=port.unit,
                kind=sample.measurement_kind,
                calibration_ref=sample.calibration_ref,
                children=(),
            )
            net_ref = endpoint_nets[Endpoint.board(ref)]
            net_values[net_ref] = sample.value
            net_measurements[net_ref] = record.measurement_id

        for ref in delay_refs:
            component = components[ref]
            value, source_measurement = delay_state[ref]
            contract = contracts[ref]
            output_port = contract.port("output")
            assert output_port is not None
            record = add_measurement(
                tick=tick,
                producer_ref=ref,
                port_ref="output",
                value=value,
                unit=output_port.unit,
                kind=MeasurementKind.MODEL_DERIVED,
                calibration_ref=None,
                children=(source_measurement,) if source_measurement else (),
            )
            net_ref = endpoint_nets[Endpoint(ref, "output")]
            net_values[net_ref] = value
            net_measurements[net_ref] = record.measurement_id
            trace.append(
                TraceEvent(
                    sequence,
                    tick,
                    ref,
                    component.semantic_profile,
                    (),
                    (("output", _value_repr(value)),),
                    (record.measurement_id,),
                    ("unit-delay output from prior tick", FUSE_STATE_SCOPE),
                )
            )
            sequence += 1

        for ref in order:
            component = components[ref]
            contract = contracts[ref]
            component_inputs: dict[str, object] = {}
            child_ids: list[str] = []
            for port in contract.ports:
                if port.direction is not PortDirection.INPUT:
                    continue
                net_ref = endpoint_nets[Endpoint(ref, port.ref)]
                if net_ref not in net_values:
                    raise SimulationError(
                        f"no value reached {ref}.{port.ref}; ordering is unresolved"
                    )
                component_inputs[port.ref] = net_values[net_ref]
                child_ids.append(net_measurements[net_ref])
            component_outputs, details = _evaluate_component(
                component,
                component_inputs,
                fuse_state,
            )
            output_ids: list[str] = []
            for port in contract.ports:
                if port.direction is not PortDirection.OUTPUT:
                    continue
                value = component_outputs[port.ref]
                _validate_value(port, value)
                record = add_measurement(
                    tick=tick,
                    producer_ref=ref,
                    port_ref=port.ref,
                    value=value,
                    unit=port.unit,
                    kind=MeasurementKind.MODEL_DERIVED,
                    calibration_ref=None,
                    children=tuple(child_ids),
                )
                net_ref = endpoint_nets[Endpoint(ref, port.ref)]
                net_values[net_ref] = value
                net_measurements[net_ref] = record.measurement_id
                output_ids.append(record.measurement_id)
            trace.append(
                TraceEvent(
                    sequence,
                    tick,
                    ref,
                    component.semantic_profile,
                    tuple(
                        (port.ref, _value_repr(component_inputs[port.ref]))
                        for port in contract.ports
                        if port.direction is PortDirection.INPUT
                    ),
                    tuple(
                        (port.ref, _value_repr(component_outputs[port.ref]))
                        for port in contract.ports
                        if port.direction is PortDirection.OUTPUT
                    ),
                    tuple(output_ids),
                    details,
                )
            )
            sequence += 1

        next_delay_state: dict[str, tuple[object, str | None]] = {}
        for ref in delay_refs:
            input_net = endpoint_nets[Endpoint(ref, "input")]
            next_delay_state[ref] = (
                net_values[input_net],
                net_measurements[input_net],
            )
        delay_state = next_delay_state

        for point in sorted(board.test_points, key=lambda item: item.ref):
            assert point.calibration_ref is not None
            calibration = calibrations[point.calibration_ref]
            value = net_values[point.net_ref]
            record = add_measurement(
                tick=tick,
                producer_ref=f"test-point:{point.ref}",
                port_ref=point.net_ref,
                value=value,
                unit=calibration.unit,
                kind=MeasurementKind.MODEL_DERIVED,
                calibration_ref=point.calibration_ref,
                children=(net_measurements[point.net_ref],),
            )
            trace.append(
                TraceEvent(
                    sequence,
                    tick,
                    f"test-point:{point.ref}",
                    "pcba8.test-point-observation.v1",
                    (("net", _value_repr(value)),),
                    ((point.net_ref, _value_repr(value)),),
                    (record.measurement_id,),
                    (
                        f"calibration={point.calibration_ref}",
                        "self-attested-structural-only",
                    ),
                )
            )
            sequence += 1

        snapshot: list[tuple[str, str]] = []
        for ref in sorted(output_ports):
            net_ref = endpoint_nets[Endpoint.board(ref)]
            value = net_values[net_ref]
            _validate_value(output_ports[ref], value)
            snapshot.append((ref, _value_repr(value)))
        output_snapshots.append((tick, tuple(snapshot)))

    outputs = tuple(output_snapshots)
    trace_items = tuple(trace)
    measurement_items = tuple(measurements)
    payload = _simulation_digest_payload(
        board_ref=board.ref,
        board_version=board.version,
        board_sha256=report.board_sha256,
        source_sha256=source_sha,
        catalog_sha256=catalog_sha,
        engine_sha256_value=engine_sha,
        decimal_context_sha256=DECIMAL_CONTEXT_SHA256,
        drc_report_sha256=report.report_sha256,
        drc_report=report,
        drc_sha256=report.drc_sha256,
        simulator_sha256=simulator_sha,
        measurement_scope_sha256=measurement_scope,
        ticks=ticks,
        outputs=outputs,
        trace=trace_items,
        measurements=measurement_items,
        boundary=fixed_research_boundary(),
    )
    return SimulationResult(
        board_ref=board.ref,
        board_version=board.version,
        board_sha256=report.board_sha256,
        source_sha256=source_sha,
        catalog_sha256=catalog_sha,
        engine_sha256=engine_sha,
        decimal_context_sha256=DECIMAL_CONTEXT_SHA256,
        drc_report_sha256=report.report_sha256,
        drc_report=report,
        drc_sha256=report.drc_sha256,
        simulator_sha256=simulator_sha,
        measurement_scope_sha256=measurement_scope,
        ticks=ticks,
        outputs=outputs,
        trace=trace_items,
        measurements=measurement_items,
        result_sha256=sha256_payload(payload),
    )
