"""Fail-closed deterministic Design Rule Check for typed PCBA v8 boards."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal
import re
from typing import Mapping

from .arithmetic import deterministic_decimal
from .contracts import (
    DEFAULT_COMPONENT_CATALOG,
    ComponentContract,
    ParameterRule,
    ParameterType,
)
from .diagnostics import (
    Diagnostic,
    DiagnosticCode,
    DrcReport,
    Severity,
)
from .finite_values import FiniteValueError, finite_value_key
from .model import (
    BOARD_ENDPOINT,
    Board,
    ComponentInstance,
    Endpoint,
)
from .types import (
    CasState,
    MeasurementKind,
    PortDirection,
    PortSpec,
    SignalKind,
    Unit,
    canonical_signal_unit,
)


SHA256_RE = re.compile(r"^[0-9A-F]{64}$")


@dataclass(frozen=True, slots=True)
class _ResolvedEndpoint:
    endpoint: Endpoint
    port: PortSpec
    is_driver: bool


def _error(
    items: list[Diagnostic],
    code: DiagnosticCode,
    subject: str,
    message: str,
) -> None:
    items.append(Diagnostic(code, Severity.ERROR, subject, message))


def _duplicate_values(values: list[str]) -> tuple[str, ...]:
    return tuple(sorted(value for value, count in Counter(values).items() if count > 1))


def _finite_decimal(value: object) -> bool:
    return type(value) is Decimal and value.is_finite()


def _validate_parameter(
    diagnostics: list[Diagnostic],
    component: ComponentInstance,
    key: str,
    value: object,
    rule: ParameterRule,
) -> None:
    subject = f"component:{component.ref}.parameter:{key}"
    if rule.value_type is ParameterType.DECIMAL:
        if not _finite_decimal(value):
            _error(
                diagnostics,
                DiagnosticCode.INVALID_PARAMETER,
                subject,
                "numeric parameters require a finite Decimal; binary floats "
                "and non-finite values are rejected",
            )
            return
        assert type(value) is Decimal
        if rule.minimum is not None and value < rule.minimum:
            _error(
                diagnostics,
                DiagnosticCode.INVALID_PARAMETER,
                subject,
                f"value {value} is below minimum {rule.minimum}",
            )
        if rule.maximum is not None:
            outside = value >= rule.maximum if rule.maximum_exclusive else value > rule.maximum
            if outside:
                relation = "exclusive maximum" if rule.maximum_exclusive else "maximum"
                _error(
                    diagnostics,
                    DiagnosticCode.INVALID_PARAMETER,
                    subject,
                    f"value {value} violates {relation} {rule.maximum}",
                )
    elif rule.value_type is ParameterType.STRING:
        if not isinstance(value, str) or not value:
            _error(
                diagnostics,
                DiagnosticCode.INVALID_PARAMETER,
                subject,
                "parameter requires a non-blank string",
            )
            return
        if rule.choices and value not in rule.choices:
            _error(
                diagnostics,
                DiagnosticCode.INVALID_PARAMETER,
                subject,
                f"value {value!r} is not one of {sorted(rule.choices)!r}",
            )


def _validate_finite_transition(
    diagnostics: list[Diagnostic], component: ComponentInstance
) -> None:
    semantics = component.finite_transition
    subject = f"component:{component.ref}.finite_transition"
    if semantics is None:
        _error(
            diagnostics,
            DiagnosticCode.INVALID_FINITE_TRANSITION,
            subject,
            "finite_transition components require an exact self-hashed transition table",
        )
        return
    problems: list[str] = []
    if semantics.profile != component.semantic_profile:
        problems.append("certificate profile does not match component semantic profile")
    if not semantics.source_name.strip() or not semantics.target_name.strip():
        problems.append("source and target object names must be non-blank")
    try:
        source_keys = tuple(finite_value_key(item) for item in semantics.source_elements)
        target_keys = tuple(finite_value_key(item) for item in semantics.target_elements)
        if len(set(source_keys)) != len(source_keys):
            problems.append("source elements are not pairwise distinct")
        if len(set(target_keys)) != len(target_keys):
            problems.append("target elements are not pairwise distinct")
    except FiniteValueError as exc:
        problems.append(f"finite element identity is unsupported: {exc}")
    if len(semantics.mapping) != len(semantics.source_elements):
        problems.append("mapping is not total on the source carrier")
    for image in semantics.mapping:
        if isinstance(image, bool) or not isinstance(image, int):
            problems.append("mapping indices must be integers")
            break
        if not 0 <= image < len(semantics.target_elements):
            problems.append("mapping contains an out-of-range target index")
            break
    if not semantics.total or not semantics.deterministic:
        problems.append("transition is not certified total and deterministic")
    if semantics.stateful or semantics.stochastic:
        problems.append("stateful or stochastic transitions are outside the finite adapter")
    try:
        digest_matches = semantics.certificate_sha256 == semantics.computed_sha256()
    except (TypeError, ValueError) as exc:
        digest_matches = False
        problems.append(f"certificate payload is not canonical: {exc}")
    if not SHA256_RE.fullmatch(semantics.certificate_sha256) or not digest_matches:
        problems.append("transition-table certificate digest is missing, malformed, or stale")
    if problems:
        _error(
            diagnostics,
            DiagnosticCode.INVALID_FINITE_TRANSITION,
            subject,
            "; ".join(dict.fromkeys(problems)),
        )


def _validate_components(
    board: Board,
    diagnostics: list[Diagnostic],
    catalog: Mapping[str, ComponentContract],
) -> dict[str, ComponentContract]:
    contracts: dict[str, ComponentContract] = {}
    for component in sorted(board.components, key=lambda item: (item.ref, item.kind)):
        subject = f"component:{component.ref}"
        contract = catalog.get(component.kind)
        if contract is None:
            _error(
                diagnostics,
                DiagnosticCode.UNKNOWN_COMPONENT_KIND,
                subject,
                f"component kind {component.kind!r} is not in the closed PCBA v8 catalog",
            )
            continue
        contracts.setdefault(component.ref, contract)
        if component.semantic_profile != contract.semantic_profile:
            _error(
                diagnostics,
                DiagnosticCode.UNRESOLVED_SEMANTICS,
                subject,
                f"semantic profile must be exactly {contract.semantic_profile!r}; "
                f"got {component.semantic_profile!r}",
            )

        unknown_parameters = sorted(set(component.parameters) - set(contract.parameters))
        for key in unknown_parameters:
            _error(
                diagnostics,
                DiagnosticCode.UNKNOWN_PARAMETER,
                f"{subject}.parameter:{key}",
                "parameter is not declared by the component contract",
            )
        for key, rule in sorted(contract.parameters.items()):
            if rule.required and key not in component.parameters:
                _error(
                    diagnostics,
                    DiagnosticCode.MISSING_PARAMETER,
                    f"{subject}.parameter:{key}",
                    "required parameter is absent",
                )
            elif key in component.parameters:
                _validate_parameter(
                    diagnostics, component, key, component.parameters[key], rule
                )

        unknown_bindings = sorted(
            set(component.state_bindings) - contract.required_state_bindings
        )
        for key in unknown_bindings:
            _error(
                diagnostics,
                DiagnosticCode.UNKNOWN_STATE_BINDING,
                f"{subject}.state:{key}",
                "state binding is not declared by the component contract",
            )
        for key in sorted(contract.required_state_bindings):
            if key not in component.state_bindings:
                _error(
                    diagnostics,
                    DiagnosticCode.MISSING_STATE_BINDING,
                    f"{subject}.state:{key}",
                    "required typed state binding is absent",
                )
            elif type(component.state_bindings[key]) is not CasState:
                _error(
                    diagnostics,
                    DiagnosticCode.INVALID_STATE_BINDING,
                    f"{subject}.state:{key}",
                    "state binding must be a typed CasState",
                )

        if component.kind == "cjt" and all(
            type(component.state_bindings.get(key)) is CasState
            for key in ("cause", "bias")
        ):
            cause = component.state_bindings["cause"]
            bias = component.state_bindings["bias"]
            if bias.domain.precedence_rank > cause.domain.precedence_rank:
                _error(
                    diagnostics,
                    DiagnosticCode.BIAS_INCOHERENT,
                    subject,
                    f"bias domain {bias.domain.value} is lower precedence than "
                    f"cause domain {cause.domain.value}",
                )
            saturation = component.parameters.get("saturation")
            cutoff = component.parameters.get("cutoff")
            if _finite_decimal(saturation) and _finite_decimal(cutoff):
                assert type(saturation) is Decimal and type(cutoff) is Decimal
                if cutoff >= saturation:
                    _error(
                        diagnostics,
                        DiagnosticCode.INVALID_PARAMETER,
                        subject,
                        f"cutoff {cutoff} must be strictly below saturation {saturation}",
                    )

        if component.kind == "fuse" and component.safety_critical:
            if component.parameters.get("action") != "permanent_block":
                _error(
                    diagnostics,
                    DiagnosticCode.UNSAFE_FUSE_ACTION,
                    subject,
                    "a safety-critical fuse must use action='permanent_block'",
                )

        if component.kind == "finite_transition":
            _validate_finite_transition(diagnostics, component)
        elif component.finite_transition is not None:
            _error(
                diagnostics,
                DiagnosticCode.UNRESOLVED_SEMANTICS,
                subject,
                "finite transition semantics are attached to a non-finite component",
            )
    return contracts


def _resolve_endpoint(
    endpoint: Endpoint,
    board_ports: Mapping[str, PortSpec],
    components: Mapping[str, ComponentInstance],
    contracts: Mapping[str, ComponentContract],
    diagnostics: list[Diagnostic],
    net_ref: str,
) -> _ResolvedEndpoint | None:
    subject = f"net:{net_ref}.endpoint:{endpoint.owner_ref}.{endpoint.port_ref}"
    if endpoint.owner_ref == BOARD_ENDPOINT:
        port = board_ports.get(endpoint.port_ref)
        if port is None:
            _error(
                diagnostics,
                DiagnosticCode.UNKNOWN_PORT,
                subject,
                "board port does not exist",
            )
            return None
        return _ResolvedEndpoint(
            endpoint,
            port,
            is_driver=port.direction is PortDirection.INPUT,
        )
    component = components.get(endpoint.owner_ref)
    if component is None:
        _error(
            diagnostics,
            DiagnosticCode.UNKNOWN_ENDPOINT_OWNER,
            subject,
            "component reference does not exist",
        )
        return None
    contract = contracts.get(endpoint.owner_ref)
    if contract is None:
        return None
    port = contract.port(endpoint.port_ref)
    if port is None:
        _error(
            diagnostics,
            DiagnosticCode.UNKNOWN_PORT,
            subject,
            f"component kind {component.kind!r} has no such port",
        )
        return None
    return _ResolvedEndpoint(
        endpoint,
        port,
        is_driver=port.direction is PortDirection.OUTPUT,
    )


def _validate_nets(
    board: Board,
    diagnostics: list[Diagnostic],
    contracts: Mapping[str, ComponentContract],
) -> tuple[
    dict[str, tuple[SignalKind, Unit]],
    dict[str, Endpoint],
    dict[Endpoint, str],
]:
    board_ports: dict[str, PortSpec] = {}
    for port in board.ports:
        board_ports.setdefault(port.ref, port)
        if not canonical_signal_unit(port.signal_kind, port.unit):
            _error(
                diagnostics,
                DiagnosticCode.INVALID_SIGNAL_UNIT_PAIR,
                f"board-port:{port.ref}",
                f"{port.signal_kind.value} cannot use unit {port.unit.value}",
            )
    components: dict[str, ComponentInstance] = {}
    for component in board.components:
        components.setdefault(component.ref, component)

    endpoint_nets: dict[Endpoint, list[str]] = defaultdict(list)
    net_types: dict[str, tuple[SignalKind, Unit]] = {}
    net_drivers: dict[str, Endpoint] = {}
    endpoint_to_net: dict[Endpoint, str] = {}

    for net in sorted(board.nets, key=lambda item: item.ref):
        resolved: list[_ResolvedEndpoint] = []
        for endpoint in net.endpoints:
            endpoint_nets[endpoint].append(net.ref)
            endpoint_to_net.setdefault(endpoint, net.ref)
            item = _resolve_endpoint(
                endpoint,
                board_ports,
                components,
                contracts,
                diagnostics,
                net.ref,
            )
            if item is not None:
                resolved.append(item)
        drivers = [item for item in resolved if item.is_driver]
        loads = [item for item in resolved if not item.is_driver]
        if len(drivers) != 1:
            _error(
                diagnostics,
                DiagnosticCode.INVALID_DRIVER_COUNT,
                f"net:{net.ref}",
                f"net requires exactly one typed driver; found {len(drivers)}",
            )
        else:
            driver = drivers[0]
            net_types.setdefault(net.ref, (driver.port.signal_kind, driver.port.unit))
            net_drivers.setdefault(net.ref, driver.endpoint)
            for load in loads:
                if load.port.signal_kind is not driver.port.signal_kind:
                    _error(
                        diagnostics,
                        DiagnosticCode.SIGNAL_KIND_MISMATCH,
                        f"net:{net.ref}",
                        f"driver kind {driver.port.signal_kind.value} cannot feed "
                        f"{load.port.signal_kind.value} at "
                        f"{load.endpoint.owner_ref}.{load.endpoint.port_ref}",
                    )
                if load.port.unit is not driver.port.unit:
                    _error(
                        diagnostics,
                        DiagnosticCode.UNIT_MISMATCH,
                        f"net:{net.ref}",
                        f"driver unit {driver.port.unit.value} cannot feed "
                        f"{load.port.unit.value} at "
                        f"{load.endpoint.owner_ref}.{load.endpoint.port_ref}",
                    )
        if not loads:
            _error(
                diagnostics,
                DiagnosticCode.MISSING_NET_LOAD,
                f"net:{net.ref}",
                "net has no input load or board output",
            )

    for endpoint, refs in sorted(
        endpoint_nets.items(), key=lambda item: (item[0].owner_ref, item[0].port_ref)
    ):
        if len(refs) > 1:
            _error(
                diagnostics,
                DiagnosticCode.PORT_MULTIPLY_CONNECTED,
                f"endpoint:{endpoint.owner_ref}.{endpoint.port_ref}",
                f"endpoint occurs on multiple nets: {sorted(refs)!r}",
            )

    for port in sorted(board.ports, key=lambda item: item.ref):
        endpoint = Endpoint.board(port.ref)
        count = len(endpoint_nets.get(endpoint, ()))
        if port.required and count == 0:
            _error(
                diagnostics,
                DiagnosticCode.REQUIRED_PORT_UNCONNECTED,
                f"board-port:{port.ref}",
                "required board port is not connected",
            )
    for component in sorted(board.components, key=lambda item: item.ref):
        contract = contracts.get(component.ref)
        if contract is None:
            continue
        for port in contract.ports:
            if not canonical_signal_unit(port.signal_kind, port.unit):
                _error(
                    diagnostics,
                    DiagnosticCode.INVALID_SIGNAL_UNIT_PAIR,
                    f"component:{component.ref}.port:{port.ref}",
                    "closed catalog contains a noncanonical signal/unit pair",
                )
            endpoint = Endpoint(component.ref, port.ref)
            count = len(endpoint_nets.get(endpoint, ()))
            if port.required and count == 0:
                _error(
                    diagnostics,
                    DiagnosticCode.REQUIRED_PORT_UNCONNECTED,
                    f"component:{component.ref}.port:{port.ref}",
                    "required component port is not connected",
                )
    return net_types, net_drivers, endpoint_to_net


def _validate_calibrations(
    board: Board,
    diagnostics: list[Diagnostic],
    net_types: Mapping[str, tuple[SignalKind, Unit]],
) -> None:
    calibrations = {}
    for calibration in board.calibrations:
        calibrations.setdefault(calibration.ref, calibration)
        problems: list[str] = []
        if not calibration.ref.strip() or not calibration.version.strip():
            problems.append("reference and version must be non-blank")
        if not SHA256_RE.fullmatch(calibration.profile_sha256):
            problems.append("profile_sha256 must be 64 uppercase hexadecimal digits")
        if type(calibration.measurement_kind) is not MeasurementKind:
            problems.append("measurement_kind must be typed")
        if type(calibration.unit) is not Unit:
            problems.append("unit must be typed")
        if (
            not calibration.instrument_identity.strip()
            or not calibration.protocol_identity.strip()
        ):
            problems.append("instrument and protocol identities must be explicit")
        if not _finite_decimal(calibration.uncertainty) or calibration.uncertainty < 0:
            problems.append("uncertainty must be a finite non-negative Decimal")
        if calibration.packet_eligible:
            problems.append(
                "self-attested calibration metadata is structural/test-only and "
                "cannot confer packet eligibility"
            )
        if problems:
            _error(
                diagnostics,
                DiagnosticCode.INVALID_CALIBRATION,
                f"calibration:{calibration.ref}",
                "; ".join(problems),
            )

    net_refs = {net.ref for net in board.nets}
    for point in sorted(board.test_points, key=lambda item: item.ref):
        subject = f"test-point:{point.ref}"
        if point.net_ref not in net_refs:
            _error(
                diagnostics,
                DiagnosticCode.UNKNOWN_TEST_POINT_NET,
                subject,
                f"net {point.net_ref!r} does not exist",
            )
            continue
        if point.calibration_ref is None:
            _error(
                diagnostics,
                DiagnosticCode.MISSING_TEST_POINT_CALIBRATION,
                subject,
                "every executable test point requires a versioned calibration reference",
            )
            continue
        calibration = calibrations.get(point.calibration_ref)
        if calibration is None:
            _error(
                diagnostics,
                DiagnosticCode.UNKNOWN_CALIBRATION,
                subject,
                f"calibration {point.calibration_ref!r} does not exist",
            )
            continue
        net_type = net_types.get(point.net_ref)
        if (
            net_type is not None
            and type(calibration.unit) is Unit
            and calibration.unit is not net_type[1]
        ):
            _error(
                diagnostics,
                DiagnosticCode.CALIBRATION_UNIT_MISMATCH,
                subject,
                f"calibration unit {calibration.unit.value} does not match "
                f"net unit {net_type[1].value}",
            )


def _validate_safety_test_points(
    board: Board,
    diagnostics: list[Diagnostic],
    contracts: Mapping[str, ComponentContract],
    endpoint_to_net: Mapping[Endpoint, str],
) -> None:
    points_by_net: dict[str, list[object]] = defaultdict(list)
    for point in board.test_points:
        points_by_net[point.net_ref].append(point)
    required: set[str] = {net.ref for net in board.nets if net.safety_critical}
    for component in board.components:
        if not component.safety_critical:
            continue
        contract = contracts.get(component.ref)
        if contract is None:
            continue
        for port in contract.ports:
            if port.direction is PortDirection.OUTPUT:
                net_ref = endpoint_to_net.get(Endpoint(component.ref, port.ref))
                if net_ref is not None:
                    required.add(net_ref)
    for net_ref in sorted(required):
        points = points_by_net.get(net_ref, ())
        if not points:
            _error(
                diagnostics,
                DiagnosticCode.MISSING_SAFETY_TEST_POINT,
                f"net:{net_ref}",
                "safety-critical path has no calibrated test point",
            )
        elif not any(point.safety_critical is True for point in points):
            _error(
                diagnostics,
                DiagnosticCode.SAFETY_TEST_POINT_NOT_MARKED,
                f"net:{net_ref}",
                "a safety-critical probe must explicitly carry safety_critical=True",
            )


def _component_graph(
    board: Board,
    net_drivers: Mapping[str, Endpoint],
) -> dict[str, set[str]]:
    graph = {component.ref: set() for component in board.components}
    for net in board.nets:
        driver = net_drivers.get(net.ref)
        if driver is None or driver.owner_ref == BOARD_ENDPOINT:
            continue
        for endpoint in net.endpoints:
            if endpoint.owner_ref not in (BOARD_ENDPOINT, driver.owner_ref):
                if endpoint.owner_ref in graph:
                    graph[driver.owner_ref].add(endpoint.owner_ref)
            elif endpoint.owner_ref == driver.owner_ref and endpoint != driver:
                graph[driver.owner_ref].add(driver.owner_ref)
    return graph


def _strongly_connected_components(graph: Mapping[str, set[str]]) -> tuple[frozenset[str], ...]:
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    low: dict[str, int] = {}
    result: list[frozenset[str]] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = index
        low[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for neighbor in sorted(graph[node]):
            if neighbor not in indices:
                visit(neighbor)
                low[node] = min(low[node], low[neighbor])
            elif neighbor in on_stack:
                low[node] = min(low[node], indices[neighbor])
        if low[node] == indices[node]:
            members: list[str] = []
            while True:
                member = stack.pop()
                on_stack.remove(member)
                members.append(member)
                if member == node:
                    break
            result.append(frozenset(members))

    for node in sorted(graph):
        if node not in indices:
            visit(node)
    cyclic = [
        component
        for component in result
        if len(component) > 1 or any(node in graph[node] for node in component)
    ]
    return tuple(sorted(cyclic, key=lambda item: tuple(sorted(item))))


def _simple_cycles(
    graph: Mapping[str, set[str]],
    members: frozenset[str],
    *,
    limit: int = 4096,
) -> tuple[tuple[str, ...], ...] | None:
    """Enumerate directed simple cycles with their lexicographically least node first."""

    cycles: set[tuple[str, ...]] = set()
    for start in sorted(members):
        path = [start]
        visited = {start}

        def visit(node: str) -> bool:
            for neighbor in sorted(graph.get(node, set()) & members):
                if neighbor == start:
                    cycles.add(tuple(path))
                    if len(cycles) > limit:
                        return False
                elif neighbor not in visited and neighbor >= start:
                    visited.add(neighbor)
                    path.append(neighbor)
                    if not visit(neighbor):
                        return False
                    path.pop()
                    visited.remove(neighbor)
            return True

        if not visit(start):
            return None
    return tuple(sorted(cycles))


def _component_gain_bound(component: ComponentInstance) -> Decimal | None:
    if component.kind in {"pass", "delay", "fuse", "mux"}:
        return Decimal("1")
    if component.kind == "scale":
        value = component.parameters.get("factor")
        return value if _finite_decimal(value) else None  # type: ignore[return-value]
    if component.kind == "cjt":
        value = component.parameters.get("beta")
        return value if _finite_decimal(value) else None  # type: ignore[return-value]
    return None


def _validate_feedback(
    board: Board,
    diagnostics: list[Diagnostic],
    contracts: Mapping[str, ComponentContract],
    net_drivers: Mapping[str, Endpoint],
) -> None:
    components = {component.ref: component for component in board.components}
    calibrations = {item.ref: item for item in board.calibrations}
    graph = _component_graph(board, net_drivers)
    cycles = _strongly_connected_components(graph)
    declarations: dict[frozenset[str], list[str]] = defaultdict(list)

    for loop in sorted(board.feedback_loops, key=lambda item: item.ref):
        subject = f"feedback:{loop.ref}"
        component_set = frozenset(loop.component_refs)
        declarations[component_set].append(loop.ref)
        invalid = False
        if len(component_set) != len(loop.component_refs) or not component_set:
            invalid = True
            _error(
                diagnostics,
                DiagnosticCode.INVALID_FEEDBACK_DECLARATION,
                subject,
                "feedback component list must be nonempty and contain no duplicates",
            )
        unknown = sorted(component_set - set(components))
        if unknown:
            invalid = True
            _error(
                diagnostics,
                DiagnosticCode.INVALID_FEEDBACK_DECLARATION,
                subject,
                f"unknown feedback components: {unknown!r}",
            )
        delay = components.get(loop.delay_component_ref)
        delay_members = {
            ref
            for ref in component_set
            if ref in components and components[ref].kind == "delay"
        }
        if (
            delay is None
            or loop.delay_component_ref not in component_set
            or delay.kind != "delay"
            or delay_members != {loop.delay_component_ref}
        ):
            invalid = True
            _error(
                diagnostics,
                DiagnosticCode.FEEDBACK_WITHOUT_DELAY,
                subject,
                "feedback requires exactly one declared unit-delay component "
                "inside the cycle",
            )
        if (
            not _finite_decimal(loop.max_round_trip_gain)
            or loop.max_round_trip_gain < 0
            or loop.max_round_trip_gain >= 1
        ):
            invalid = True
            _error(
                diagnostics,
                DiagnosticCode.UNSAFE_FEEDBACK_GAIN,
                subject,
                "round-trip gain must be a finite Decimal in [0,1)",
            )
        declared_cycles = (
            _simple_cycles(graph, component_set)
            if not unknown and component_set
            else ()
        )
        if declared_cycles is None:
            invalid = True
            _error(
                diagnostics,
                DiagnosticCode.UNRESOLVED_SAFETY_ANALYSIS,
                subject,
                "feedback cycle enumeration exceeded the conservative resource bound",
            )
        else:
            for cycle in declared_cycles:
                derived_gain = Decimal("1")
                derived_resolved = True
                for ref in cycle:
                    factor = _component_gain_bound(components[ref])
                    if factor is None:
                        derived_resolved = False
                        break
                    derived_gain *= factor
                cycle_label = "->".join((*cycle, cycle[0]))
                if not derived_resolved:
                    invalid = True
                    _error(
                        diagnostics,
                        DiagnosticCode.UNRESOLVED_SAFETY_ANALYSIS,
                        subject,
                        f"gain cannot be derived for directed cycle {cycle_label}",
                    )
                elif derived_gain >= 1 or (
                    _finite_decimal(loop.max_round_trip_gain)
                    and derived_gain > loop.max_round_trip_gain
                ):
                    invalid = True
                    _error(
                        diagnostics,
                        DiagnosticCode.UNSAFE_FEEDBACK_GAIN,
                        subject,
                        f"directed cycle {cycle_label} has gain bound "
                        f"{derived_gain}, outside declared sub-unity bound "
                        f"{loop.max_round_trip_gain}",
                    )
        calibration = calibrations.get(loop.calibration_ref)
        if calibration is None or calibration.unit is not Unit.NONE:
            invalid = True
            _error(
                diagnostics,
                DiagnosticCode.UNKNOWN_CALIBRATION,
                subject,
                "feedback gain requires an existing dimensionless calibration",
            )
        if component_set not in cycles and not invalid:
            _error(
                diagnostics,
                DiagnosticCode.INVALID_FEEDBACK_DECLARATION,
                subject,
                "declared component set is not an actual graph cycle",
            )

    for cycle in cycles:
        refs = declarations.get(cycle, ())
        if not refs:
            _error(
                diagnostics,
                DiagnosticCode.UNDECLARED_FEEDBACK,
                "feedback-cycle:" + ",".join(sorted(cycle)),
                "every graph cycle must have an exact, calibrated, sub-unity declaration",
            )
        elif len(refs) > 1:
            _error(
                diagnostics,
                DiagnosticCode.INVALID_FEEDBACK_DECLARATION,
                "feedback-cycle:" + ",".join(sorted(cycle)),
                f"cycle has multiple declarations: {sorted(refs)!r}",
            )


def _activation_upper_bounds(
    board: Board,
    contracts: Mapping[str, ComponentContract],
    endpoint_to_net: Mapping[Endpoint, str],
) -> dict[str, Decimal]:
    bounds: dict[str, Decimal] = {}
    for port in board.ports:
        if (
            port.direction is PortDirection.INPUT
            and port.signal_kind is SignalKind.ACTIVATION
        ):
            net = endpoint_to_net.get(Endpoint.board(port.ref))
            if net is not None:
                bounds[net] = Decimal("1")

    components = {component.ref: component for component in board.components}
    for _ in range(max(1, len(components) + 1)):
        changed = False
        for ref in sorted(components):
            component = components[ref]
            contract = contracts.get(ref)
            if contract is None:
                continue
            inputs = {
                port.ref: bounds.get(endpoint_to_net.get(Endpoint(ref, port.ref), ""))
                for port in contract.ports
                if port.direction is PortDirection.INPUT
                and port.signal_kind is SignalKind.ACTIVATION
            }
            output_bound: Decimal | None = None
            if component.kind == "cjt":
                cause_bound = inputs.get("cause")
                bias_bound = inputs.get("bias")
                beta = component.parameters.get("beta")
                saturation = component.parameters.get("saturation")
                cutoff = component.parameters.get("cutoff")
                if (
                    cause_bound is not None
                    and bias_bound is not None
                    and _finite_decimal(beta)
                    and _finite_decimal(saturation)
                    and _finite_decimal(cutoff)
                ):
                    assert type(beta) is Decimal
                    assert type(saturation) is Decimal
                    assert type(cutoff) is Decimal
                    if bias_bound <= cutoff:
                        output_bound = Decimal("0")
                    else:
                        output_bound = min(
                            saturation,
                            beta * cause_bound * bias_bound,
                        )
            elif component.kind == "pass":
                output_bound = inputs.get("input")
            elif component.kind == "scale":
                factor = component.parameters.get("factor")
                ceiling = component.parameters.get("ceiling")
                source = inputs.get("input")
                if source is not None and _finite_decimal(factor) and _finite_decimal(ceiling):
                    output_bound = min(ceiling, source * factor)  # type: ignore[arg-type]
            elif component.kind == "mux":
                candidates = (inputs.get("when_false"), inputs.get("when_true"))
                if all(item is not None for item in candidates):
                    output_bound = max(candidates)  # type: ignore[arg-type]
            elif component.kind == "fuse":
                output_bound = inputs.get("input")
            elif component.kind == "delay":
                output_bound = Decimal("1")
            if output_bound is None:
                continue
            for port in contract.ports:
                if (
                    port.direction is PortDirection.OUTPUT
                    and port.signal_kind is SignalKind.ACTIVATION
                ):
                    net = endpoint_to_net.get(Endpoint(ref, port.ref))
                    if net is not None and bounds.get(net) != output_bound:
                        bounds[net] = output_bound
                        changed = True
        if not changed:
            break
    return bounds


def _validate_safety_thresholds(
    board: Board,
    diagnostics: list[Diagnostic],
    contracts: Mapping[str, ComponentContract],
    endpoint_to_net: Mapping[Endpoint, str],
) -> None:
    bounds = _activation_upper_bounds(board, contracts, endpoint_to_net)
    for component in sorted(board.components, key=lambda item: item.ref):
        if component.kind != "fuse":
            continue
        threshold = component.parameters.get("threshold")
        if not _finite_decimal(threshold):
            continue
        input_net = endpoint_to_net.get(Endpoint(component.ref, "input"))
        bound = bounds.get(input_net or "")
        if bound is None:
            if component.safety_critical:
                _error(
                    diagnostics,
                    DiagnosticCode.UNRESOLVED_SAFETY_ANALYSIS,
                    f"component:{component.ref}",
                    "safety-critical fuse input bound cannot be resolved",
                )
            continue
        assert type(threshold) is Decimal
        if bound < threshold:
            _error(
                diagnostics,
                DiagnosticCode.UNREACHABLE_SAFETY_THRESHOLD,
                f"component:{component.ref}",
                f"maximum upstream activation {bound} is below fuse threshold "
                f"{threshold}; the fuse cannot trip",
            )


@deterministic_decimal
def _collect_diagnostics(
    board: Board,
    *,
    catalog: Mapping[str, ComponentContract] = DEFAULT_COMPONENT_CATALOG,
) -> tuple[Diagnostic, ...]:
    """Return the exact diagnostics without minting a report artifact."""

    diagnostics: list[Diagnostic] = []
    if type(board) is not Board:
        raise TypeError("validate_board requires a Board")
    board.revalidate()
    if catalog is not DEFAULT_COMPONENT_CATALOG:
        raise ValueError("the closed PCBA v8 component catalog cannot be overridden")
    if not board.ref.strip() or not board.version.strip():
        _error(
            diagnostics,
            DiagnosticCode.INVALID_BOARD_METADATA,
            "board",
            "board reference and version must be non-blank",
        )

    reference_groups = {
        "board-port": [item.ref for item in board.ports],
        "component": [item.ref for item in board.components],
        "net": [item.ref for item in board.nets],
        "test-point": [item.ref for item in board.test_points],
        "calibration": [item.ref for item in board.calibrations],
        "feedback": [item.ref for item in board.feedback_loops],
    }
    for group, values in reference_groups.items():
        for index, value in enumerate(values):
            if type(value) is not str or not value.strip():
                _error(
                    diagnostics,
                    DiagnosticCode.INVALID_BOARD_METADATA,
                    f"{group}[{index}]",
                    f"{group} references must be non-blank strings",
                )
        for value in _duplicate_values(values):
            _error(
                diagnostics,
                DiagnosticCode.DUPLICATE_REFERENCE,
                f"{group}:{value}",
                f"duplicate {group} reference is forbidden",
            )

    contracts = _validate_components(board, diagnostics, catalog)
    net_types, net_drivers, endpoint_to_net = _validate_nets(
        board, diagnostics, contracts
    )
    _validate_calibrations(board, diagnostics, net_types)
    _validate_safety_test_points(board, diagnostics, contracts, endpoint_to_net)
    _validate_feedback(board, diagnostics, contracts, net_drivers)
    _validate_safety_thresholds(board, diagnostics, contracts, endpoint_to_net)

    return tuple(sorted(diagnostics, key=lambda item: item.sort_key))


@deterministic_decimal
def validate_board(
    board: Board,
    *,
    catalog: Mapping[str, ComponentContract] = DEFAULT_COMPONENT_CATALOG,
) -> DrcReport:
    """Validate a board and return a deterministically ordered fail-closed report."""

    diagnostics = _collect_diagnostics(board, catalog=catalog)
    return DrcReport.create(
        board=board,
        diagnostics=diagnostics,
    )
