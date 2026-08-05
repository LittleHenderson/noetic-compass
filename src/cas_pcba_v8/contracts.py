"""Closed component catalog for the PCBA v8 executable research core."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from .integrity import require_safe_reference, sha256_payload
from .types import PortDirection, PortSpec, SignalKind, Unit


class ParameterType(str, Enum):
    DECIMAL = "DECIMAL"
    STRING = "STRING"


@dataclass(frozen=True, slots=True)
class ParameterRule:
    value_type: ParameterType
    required: bool = True
    minimum: Decimal | None = None
    maximum: Decimal | None = None
    maximum_exclusive: bool = False
    choices: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if type(self) is not ParameterRule:
            raise TypeError("ParameterRule subclasses are not accepted")
        object.__setattr__(self, "choices", frozenset(self.choices))
        self.revalidate()

    def revalidate(self) -> None:
        if type(self) is not ParameterRule:
            raise TypeError("parameter rules must use the exact type")
        if type(self.value_type) is not ParameterType:
            raise TypeError("parameter rule value_type must be typed")
        if type(self.required) is not bool or type(self.maximum_exclusive) is not bool:
            raise TypeError("parameter rule flags must be exact booleans")
        for field_name in ("minimum", "maximum"):
            value = getattr(self, field_name)
            if value is not None and (
                type(value) is not Decimal or not value.is_finite()
            ):
                raise TypeError(f"parameter rule {field_name} must be finite Decimal")
        if (
            self.minimum is not None
            and self.maximum is not None
            and self.minimum > self.maximum
        ):
            raise ValueError("parameter rule minimum cannot exceed maximum")
        if type(self.choices) is not frozenset or any(
            type(item) is not str for item in self.choices
        ):
            raise TypeError("parameter rule choices must be exact strings")
        for item in self.choices:
            require_safe_reference(item, "ParameterRule choice")


@dataclass(frozen=True, slots=True)
class ComponentContract:
    kind: str
    semantic_profile: str
    ports: tuple[PortSpec, ...]
    parameters: Mapping[str, ParameterRule]
    required_state_bindings: frozenset[str] = frozenset()
    deterministic: bool = True
    stateful: bool = False
    tks_finite_adapter_eligible: bool = False

    def __post_init__(self) -> None:
        if type(self) is not ComponentContract:
            raise TypeError("ComponentContract subclasses are not accepted")
        object.__setattr__(self, "ports", tuple(self.ports))
        object.__setattr__(
            self,
            "parameters",
            MappingProxyType(dict(self.parameters)),
        )
        object.__setattr__(
            self,
            "required_state_bindings",
            frozenset(self.required_state_bindings),
        )
        self.revalidate()

    def revalidate(self) -> None:
        if type(self) is not ComponentContract:
            raise TypeError("component contracts must use the exact type")
        require_safe_reference(self.kind, "ComponentContract.kind")
        require_safe_reference(
            self.semantic_profile,
            "ComponentContract.semantic_profile",
        )
        if type(self.ports) is not tuple or any(
            type(port) is not PortSpec for port in self.ports
        ):
            raise TypeError("component contract ports must be exact PortSpec values")
        for port in self.ports:
            port.revalidate()
        if type(self.parameters) is not MappingProxyType or any(
            type(ref) is not str or type(rule) is not ParameterRule
            for ref, rule in self.parameters.items()
        ):
            raise TypeError("component contract parameters must remain exactly typed")
        for ref, rule in self.parameters.items():
            require_safe_reference(ref, "ComponentContract parameter ref")
            rule.revalidate()
        if type(self.required_state_bindings) is not frozenset or any(
            type(ref) is not str for ref in self.required_state_bindings
        ):
            raise TypeError("component state-binding declarations must be exact strings")
        for ref in self.required_state_bindings:
            require_safe_reference(ref, "ComponentContract state-binding ref")
        for field_name in (
            "deterministic",
            "stateful",
            "tks_finite_adapter_eligible",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise TypeError(f"ComponentContract.{field_name} must be bool")

    def port(self, ref: str) -> PortSpec | None:
        self.revalidate()
        require_safe_reference(ref, "ComponentContract.port ref")
        return next((port for port in self.ports if port.ref == ref), None)


ACTIVATION_IN = lambda ref: PortSpec(  # noqa: E731 - compact catalog declaration
    ref, PortDirection.INPUT, SignalKind.ACTIVATION, Unit.ACTIVATION_0_1
)
ACTIVATION_OUT = lambda ref: PortSpec(  # noqa: E731
    ref, PortDirection.OUTPUT, SignalKind.ACTIVATION, Unit.ACTIVATION_0_1
)


def _rules(**values: ParameterRule) -> Mapping[str, ParameterRule]:
    return MappingProxyType(values)


DECIMAL_NONNEGATIVE = ParameterRule(ParameterType.DECIMAL, minimum=Decimal("0"))
ACTIVATION_LEVEL = ParameterRule(
    ParameterType.DECIMAL,
    minimum=Decimal("0"),
    maximum=Decimal("1"),
)


DEFAULT_COMPONENT_CATALOG: Mapping[str, ComponentContract] = MappingProxyType(
    {
        "pass": ComponentContract(
            kind="pass",
            semantic_profile="pcba8.pass.v0",
            ports=(ACTIVATION_IN("input"), ACTIVATION_OUT("output")),
            parameters=_rules(),
        ),
        "scale": ComponentContract(
            kind="scale",
            semantic_profile="pcba8.scale.v0",
            ports=(ACTIVATION_IN("input"), ACTIVATION_OUT("output")),
            parameters=_rules(
                factor=DECIMAL_NONNEGATIVE,
                ceiling=ACTIVATION_LEVEL,
            ),
        ),
        "cjt": ComponentContract(
            kind="cjt",
            semantic_profile="pcba8.cjt.reference.v0",
            ports=(
                ACTIVATION_IN("cause"),
                ACTIVATION_IN("bias"),
                ACTIVATION_OUT("effect"),
            ),
            parameters=_rules(
                beta=DECIMAL_NONNEGATIVE,
                saturation=ACTIVATION_LEVEL,
                cutoff=ACTIVATION_LEVEL,
            ),
            required_state_bindings=frozenset({"cause", "bias", "effect"}),
        ),
        "decision_threshold": ComponentContract(
            kind="decision_threshold",
            semantic_profile="pcba8.decision-threshold.v0",
            ports=(
                ACTIVATION_IN("input"),
                PortSpec(
                    "decision",
                    PortDirection.OUTPUT,
                    SignalKind.DECISION,
                    Unit.BOOLEAN,
                ),
            ),
            parameters=_rules(threshold=ACTIVATION_LEVEL),
        ),
        "mux": ComponentContract(
            kind="mux",
            semantic_profile="pcba8.mux.v0",
            ports=(
                ACTIVATION_IN("when_false"),
                ACTIVATION_IN("when_true"),
                PortSpec(
                    "select",
                    PortDirection.INPUT,
                    SignalKind.DECISION,
                    Unit.BOOLEAN,
                ),
                ACTIVATION_OUT("output"),
            ),
            parameters=_rules(),
        ),
        "fuse": ComponentContract(
            kind="fuse",
            semantic_profile="pcba8.fuse.reference.v0",
            ports=(ACTIVATION_IN("input"), ACTIVATION_OUT("output")),
            parameters=_rules(
                threshold=ACTIVATION_LEVEL,
                action=ParameterRule(
                    ParameterType.STRING,
                    choices=frozenset({"permanent_block", "warn"}),
                ),
            ),
            stateful=True,
        ),
        "delay": ComponentContract(
            kind="delay",
            semantic_profile="pcba8.unit-delay.v0",
            ports=(ACTIVATION_IN("input"), ACTIVATION_OUT("output")),
            parameters=_rules(initial=ACTIVATION_LEVEL),
            stateful=True,
        ),
        "finite_transition": ComponentContract(
            kind="finite_transition",
            semantic_profile="pcba8.finite-transition.v0",
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
            parameters=_rules(),
            tks_finite_adapter_eligible=True,
        ),
    }
)


CATALOG_PROFILE = "cas-pcba-v8.closed-component-catalog.v1"
CATALOG_SHA256 = "579342E00448EDD62BF85E468DE638EBDF83B282A0279BCD23652E197A1C1D0A"


def component_catalog_payload() -> dict[str, object]:
    if type(DEFAULT_COMPONENT_CATALOG) is not MappingProxyType:
        raise RuntimeError("closed component catalog container was substituted")
    if any(
        type(kind) is not str or type(contract) is not ComponentContract
        for kind, contract in DEFAULT_COMPONENT_CATALOG.items()
    ):
        raise RuntimeError("closed component catalog entries were substituted")
    for kind, contract in DEFAULT_COMPONENT_CATALOG.items():
        require_safe_reference(kind, "component catalog kind")
        contract.revalidate()
        if kind != contract.kind:
            raise RuntimeError("component catalog key/contract identity diverged")
    payload = {
        "profile": CATALOG_PROFILE,
        "components": [
            {
                "kind": contract.kind,
                "semantic_profile": contract.semantic_profile,
                "ports": [
                    {
                        "ref": port.ref,
                        "direction": port.direction.value,
                        "signal_kind": port.signal_kind.value,
                        "unit": port.unit.value,
                        "required": port.required,
                    }
                    for port in contract.ports
                ],
                "parameters": [
                    {
                        "ref": ref,
                        "value_type": rule.value_type.value,
                        "required": rule.required,
                        "minimum": str(rule.minimum)
                        if rule.minimum is not None
                        else None,
                        "maximum": str(rule.maximum)
                        if rule.maximum is not None
                        else None,
                        "maximum_exclusive": rule.maximum_exclusive,
                        "choices": sorted(rule.choices),
                    }
                    for ref, rule in sorted(contract.parameters.items())
                ],
                "required_state_bindings": sorted(
                    contract.required_state_bindings
                ),
                "deterministic": contract.deterministic,
                "stateful": contract.stateful,
                "tks_finite_adapter_eligible": (
                    contract.tks_finite_adapter_eligible
                ),
            }
            for _, contract in sorted(DEFAULT_COMPONENT_CATALOG.items())
        ],
    }
    if sha256_payload(payload) != CATALOG_SHA256:
        raise RuntimeError("closed component catalog identity is stale or tampered")
    return payload


def component_catalog_sha256() -> str:
    component_catalog_payload()
    return CATALOG_SHA256
