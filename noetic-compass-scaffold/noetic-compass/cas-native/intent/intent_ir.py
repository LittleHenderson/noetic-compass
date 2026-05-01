"""Typed IntentIR contract for CAS/NL recovery.

IntentIR is the boundary between natural language interpretation and formal
CAS construction. The model may predict or score this structure, but compiler
validation and deterministic builders own the final CAS expression.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


DOMAINS: tuple[str, ...] = ("P", "C", "E", "O")
DRIVES: tuple[str, ...] = ("F1", "F2", "F3", "F4", "F5", "F6", "F7")
REGISTERS: tuple[str, ...] = ("T", "A", "f", "E")
REGISTER_MODES: tuple[str, ...] = (
    "none",
    "single",
    "set_spec",
    "co_presence",
    "integration",
)
EXPRESSION_FAMILIES: tuple[str, ...] = (
    "state",
    "register_state",
    "production",
    "rule_four",
    "omega",
    "meta_logic",
)
TRANSITION_KINDS: tuple[str, ...] = (
    "state",
    "relation",
    "membership",
    "subset",
    "cluster_update",
    "rpm_gate",
    "production",
    "omega_bind",
    "inversion_check",
    "meta_logic_move",
    "surface_act",
    "ask_clarify",
    "repair",
)
META_RELATIONS: tuple[str, ...] = (
    "membership",
    "subset",
    "product",
    "cover",
    "partition",
    "pullback",
    "authority",
    "evidence",
    "trace_nesting",
)
AUTHORITY_LABELS: tuple[str, ...] = ("none", "admitted", "blocked")


@dataclass(frozen=True)
class StateAtom:
    """One typed CAS state reference such as ``^2^P_{F4}|A``."""

    noetic: int
    domain: str | None = None
    drive: str | None = None
    register: str | None = None

    def to_cas(self) -> str:
        value = f"^{self.noetic}"
        if self.domain is not None:
            value += f"^{self.domain}"
        if self.drive is not None:
            value += f"_{{{self.drive}}}"
        if self.register is not None:
            value += f"|{self.register}"
        return value

    def to_dict(self) -> dict[str, Any]:
        return {
            "noetic": self.noetic,
            "domain": self.domain,
            "drive": self.drive,
            "register": self.register,
            "cas": self.to_cas(),
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.noetic < 0 or self.noetic > 9:
            errors.append(f"state atom noetic must be 0-9, got {self.noetic}")
        if self.domain is not None and self.domain not in DOMAINS:
            errors.append(f"{self.to_cas()}: unknown domain {self.domain!r}")
        if self.drive is not None and self.drive not in DRIVES:
            errors.append(f"{self.to_cas()}: unknown drive {self.drive!r}")
        if self.register is not None and self.register not in REGISTERS:
            errors.append(f"{self.to_cas()}: unknown register {self.register!r}")
        return errors


@dataclass(frozen=True)
class AxisBinding:
    """Primary predicted axes for a turn, plus the states they bind to."""

    noetic: int | None = None
    domain: str | None = None
    drive: str | None = None
    register: str | None = None
    states: tuple[StateAtom, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "noetic": self.noetic,
            "domain": self.domain,
            "drive": self.drive,
            "register": self.register,
            "states": [state.to_dict() for state in self.states],
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.noetic is not None and (self.noetic < 0 or self.noetic > 9):
            errors.append(f"axis noetic must be 0-9, got {self.noetic}")
        if self.domain is not None and self.domain not in DOMAINS:
            errors.append(f"axis has unknown domain {self.domain!r}")
        if self.drive is not None and self.drive not in DRIVES:
            errors.append(f"axis has unknown drive {self.drive!r}")
        if self.register is not None and self.register not in REGISTERS:
            errors.append(f"axis has unknown register {self.register!r}")
        for state in self.states:
            errors.extend(state.validate())
        return errors


@dataclass(frozen=True)
class RegisterIntent:
    """Typed v7.5/v7.7 register binding intent."""

    mode: str = "none"
    registers: tuple[str, ...] = ()
    omega_target: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "registers": list(self.registers),
            "omega_target": self.omega_target,
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.mode not in REGISTER_MODES:
            errors.append(f"unknown register mode {self.mode!r}")
        unknown = sorted(register for register in self.registers if register not in REGISTERS)
        if unknown:
            errors.append(f"unknown register(s) {unknown}")
        if self.mode == "none" and self.registers:
            errors.append("register mode none cannot carry registers")
        if self.mode == "single" and len(self.registers) != 1:
            errors.append("single register mode requires exactly one register")
        if self.mode in {"set_spec", "co_presence", "integration"} and len(self.registers) < 2:
            errors.append(f"{self.mode} register mode requires at least two registers")
        if self.mode == "integration" and not self.omega_target:
            errors.append("integration register mode requires omega_target")
        if self.mode != "integration" and self.omega_target:
            errors.append(f"{self.mode} register mode must not carry omega_target")
        return errors


@dataclass(frozen=True)
class ProductionIngredientIntent:
    """One typed ingredient in a production recipe."""

    state: StateAtom
    coefficient: float = 1.0
    available: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.to_dict(),
            "coefficient": self.coefficient,
            "available": self.available,
        }

    def validate(self) -> list[str]:
        errors = self.state.validate()
        if self.coefficient <= 0:
            errors.append(f"{self.state.to_cas()}: coefficient must be > 0")
        if self.available is not None and self.available < 0:
            errors.append(f"{self.state.to_cas()}: available must be >= 0")
        return errors


@dataclass(frozen=True)
class ProductionIntent:
    """Typed v7.6 production semantics intent."""

    omega_target: str
    ingredients: tuple[ProductionIngredientIntent, ...]
    leakage_terms: tuple[str, ...] = ()
    catalysts: tuple[str, ...] = ()
    inhibitors: tuple[str, ...] = ()
    limiting_reagent: str | None = None
    theoretical_yield: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "omega_target": self.omega_target,
            "ingredients": [ingredient.to_dict() for ingredient in self.ingredients],
            "leakage_terms": list(self.leakage_terms),
            "catalysts": list(self.catalysts),
            "inhibitors": list(self.inhibitors),
            "limiting_reagent": self.limiting_reagent,
            "theoretical_yield": self.theoretical_yield,
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.omega_target:
            errors.append("production intent requires omega_target")
        if not self.ingredients:
            errors.append("production intent requires at least one ingredient")
        for ingredient in self.ingredients:
            errors.extend(ingredient.validate())
        if self.theoretical_yield is not None and self.theoretical_yield < 0:
            errors.append("theoretical_yield must be >= 0 when present")
        return errors


@dataclass(frozen=True)
class MetaLogicIntent:
    """Typed meta-logic intent extracted from set/product/authority forms."""

    relations: tuple[str, ...] = ()
    carriers: tuple[str, ...] = ()
    objects: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "relations": list(self.relations),
            "carriers": list(self.carriers),
            "objects": list(self.objects),
        }

    def validate(self) -> list[str]:
        unknown = sorted(relation for relation in self.relations if relation not in META_RELATIONS)
        if unknown:
            return [f"unknown meta relation(s) {unknown}"]
        return []


@dataclass(frozen=True)
class EvidenceSpan:
    """Text span that supports an IntentIR field."""

    source_field: str
    text: str
    role: str

    def to_dict(self) -> dict[str, str]:
        return {
            "source_field": self.source_field,
            "text": self.text,
            "role": self.role,
        }


@dataclass(frozen=True)
class AmbiguityOption:
    """Unresolved alternative preserved instead of collapsed away."""

    path: str
    candidates: tuple[str, ...]
    reason: str
    confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "candidates": list(self.candidates),
            "reason": self.reason,
            "confidence": self.confidence,
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.path:
            errors.append("ambiguity option requires path")
        if not self.candidates:
            errors.append(f"{self.path}: ambiguity option requires candidates")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            errors.append(f"{self.path}: confidence must be within [0, 1]")
        return errors


@dataclass(frozen=True)
class BuilderTarget:
    """The deterministic builder and canonical expression this intent targets."""

    family: str
    builder: str
    canonical_expression: str | None = None
    requires_compiler_validation: bool = True
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "builder": self.builder,
            "canonical_expression": self.canonical_expression,
            "requires_compiler_validation": self.requires_compiler_validation,
            "confidence": self.confidence,
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.family not in EXPRESSION_FAMILIES:
            errors.append(f"unknown builder target family {self.family!r}")
        if not self.builder:
            errors.append("builder target requires builder")
        if not 0.0 <= self.confidence <= 1.0:
            errors.append("builder target confidence must be within [0, 1]")
        return errors


@dataclass(frozen=True)
class IntentIR:
    """A recoverable CAS intent before formal construction and rendering."""

    id: str
    user_prompt: str
    turn_type: str
    expression_family: str
    transition_kind: str
    axis: AxisBinding = field(default_factory=AxisBinding)
    register_intent: RegisterIntent = field(default_factory=RegisterIntent)
    omega_targets: tuple[str, ...] = ()
    production: ProductionIntent | None = None
    meta_logic: MetaLogicIntent | None = None
    builder_targets: tuple[BuilderTarget, ...] = ()
    evidence_spans: tuple[EvidenceSpan, ...] = ()
    ambiguities: tuple[AmbiguityOption, ...] = ()
    authority: str = "none"
    confidence: float = 1.0
    source_level2_id: str | None = None
    cas_expression_target: str | None = None
    tags: tuple[str, ...] = ()
    provenance: dict[str, Any] = field(default_factory=dict)
    schema_version: str = "intent_ir.v1"

    def model_input_text(self) -> str:
        """Return the only text allowed to enter the NL encoder."""

        return self.user_prompt

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "source_level2_id": self.source_level2_id,
            "user_prompt": self.user_prompt,
            "turn_type": self.turn_type,
            "expression_family": self.expression_family,
            "transition_kind": self.transition_kind,
            "axis": self.axis.to_dict(),
            "register_intent": self.register_intent.to_dict(),
            "omega_targets": list(self.omega_targets),
            "production": self.production.to_dict() if self.production else None,
            "meta_logic": self.meta_logic.to_dict() if self.meta_logic else None,
            "builder_targets": [target.to_dict() for target in self.builder_targets],
            "evidence_spans": [span.to_dict() for span in self.evidence_spans],
            "ambiguities": [option.to_dict() for option in self.ambiguities],
            "authority": self.authority,
            "confidence": self.confidence,
            "cas_expression_target": self.cas_expression_target,
            "tags": list(self.tags),
            "provenance": self.provenance,
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.id:
            errors.append("IntentIR requires id")
        if not self.user_prompt:
            errors.append("IntentIR requires user_prompt")
        if self.expression_family not in EXPRESSION_FAMILIES:
            errors.append(f"unknown expression family {self.expression_family!r}")
        if self.transition_kind not in TRANSITION_KINDS:
            errors.append(f"unknown transition kind {self.transition_kind!r}")
        if self.authority not in AUTHORITY_LABELS:
            errors.append(f"unknown authority label {self.authority!r}")
        if not 0.0 <= self.confidence <= 1.0:
            errors.append("IntentIR confidence must be within [0, 1]")

        errors.extend(self.axis.validate())
        errors.extend(self.register_intent.validate())
        if self.production is not None:
            errors.extend(self.production.validate())
        if self.meta_logic is not None:
            errors.extend(self.meta_logic.validate())
        for target in self.builder_targets:
            errors.extend(target.validate())
        for option in self.ambiguities:
            errors.extend(option.validate())

        if self.expression_family == "production" and self.production is None:
            errors.append("production family requires production intent")
        if self.expression_family == "meta_logic" and self.meta_logic is None:
            errors.append("meta_logic family requires meta_logic intent")
        return errors
