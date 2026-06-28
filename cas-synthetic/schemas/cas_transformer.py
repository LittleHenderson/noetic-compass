"""Schemas for CAS Transformer turn-level training records.

These classes define the first CAS Transformer data wedge: every conversational
record must carry a CAS trace and a typed meta-logic context. They are pure
stdlib dataclasses so the synthetic generator can use them without introducing
runtime dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


TURN_TYPES = {
    "OPEN",
    "ACK",
    "MIRROR",
    "CLARIFY",
    "EMPATHIZE",
    "ANSWER",
    "PLAN",
    "REFUSE",
    "REFUSE_CLAIM",
    "REPAIR",
    "CLOSE",
}

RELATION_TYPES = {
    "member",
    "not_member",
    "subset",
    "proper_subset",
    "superset",
    "union",
    "intersection",
    "difference",
    "product",
    "cover",
    "partition",
    "pullback",
    "licenses",
    "depends_on",
    "supports",
    "contains",
}

TURN_PRECONDITIONS = {
    "OPEN": {"channel_idle"},
    "ACK": {"input_received"},
    "MIRROR": {"user_intent_present"},
    "CLARIFY": {"lacunarity_detected"},
    "EMPATHIZE": {"affect_detected"},
    "ANSWER": {"task_active", "claim_supported"},
    "PLAN": {"task_active"},
    "REFUSE": {"boundary_violation"},
    "REFUSE_CLAIM": {"evidence_gap"},
    "REPAIR": {"prior_error_detected"},
    "CLOSE": {"response_delivered"},
}

TIGHT_TURN_TYPES = {"ANSWER", "REFUSE", "REFUSE_CLAIM", "REPAIR", "CLARIFY"}
SHELL_TURN_TYPES = {"OPEN", "ACK", "MIRROR", "EMPATHIZE", "PLAN", "CLOSE"}
VALIDATION_PHASES = ("structural", "meta_logic", "tight_semantics")

SET_KINDS = {"set", "cluster", "carrier", "product", "cover", "partition", "pullback"}
ELEMENT_KINDS = {"element", "trace_node", "claim", "utterance", "tool_observation", "response"}
ANY_CARRIER = "Any"
DOMAINS = ("P", "C", "E", "O")
REGISTER_VALUES = {"T", "A", "f", "E"}
REGISTER_MODES = {"single", "set_spec", "co_presence", "integration"}

ALLOWED_LICENSES = {
    ("ToolObservationSet", "EvidenceSet"),
    ("EvidenceSet", "ValidatedClaimSet"),
    ("ValidatedClaimSet", "RenderedResponseSet"),
    ("UserRequestSet", "TaskIntentSet"),
    ("TaskIntentSet", "CASActionSet"),
    ("SystemInstructionSet", "CASActionSet"),
    ("DeveloperInstructionSet", "CASActionSet"),
}

BLOCKED_LICENSES = {
    ("UserRequestSet", "SystemInstructionSet"),
    ("UserRequestSet", "DeveloperInstructionSet"),
    ("ToolObservationSet", "SystemInstructionSet"),
    ("RenderedResponseSet", "SystemInstructionSet"),
}


@dataclass(frozen=True)
class ValidationDiagnostic:
    """Structured validation diagnostic for repair/resample feedback."""

    phase: str
    code: str
    message: str
    severity: str = "error"
    fixable: bool = True
    suggestion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "phase": self.phase,
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "fixable": self.fixable,
        }
        if self.suggestion is not None:
            result["suggestion"] = self.suggestion
        return result


@dataclass(frozen=True)
class MetaLogicObject:
    """Typed object in the meta-logic graph."""

    name: str
    kind: str
    carrier: str = ANY_CARRIER

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "kind": self.kind,
            "carrier": self.carrier,
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.name:
            errors.append("meta-logic object has empty name")
        if self.kind not in SET_KINDS | ELEMENT_KINDS:
            errors.append(f"{self.name}: unknown kind {self.kind!r}")
        if not self.carrier:
            errors.append(f"{self.name}: empty carrier")
        return errors


@dataclass(frozen=True)
class MetaLogicRelation:
    """Typed relation between meta-logic objects."""

    relation: str
    source: str
    target: str

    def to_dict(self) -> dict[str, str]:
        return {
            "relation": self.relation,
            "source": self.source,
            "target": self.target,
        }

    def validate(self, objects: dict[str, MetaLogicObject]) -> list[str]:
        errors: list[str] = []
        if self.relation not in RELATION_TYPES:
            errors.append(f"{self.source}->{self.target}: unknown relation {self.relation!r}")
        if self.source not in objects:
            errors.append(f"{self.source}->{self.target}: unknown source object")
        if self.target not in objects:
            errors.append(f"{self.source}->{self.target}: unknown target object")
        if errors:
            return errors

        source = objects[self.source]
        target = objects[self.target]

        if self.relation in {"member", "not_member"}:
            if target.kind not in SET_KINDS:
                errors.append(
                    f"{self.source} {self.relation} {self.target}: target must be set-like"
                )
            if source.kind in SET_KINDS:
                errors.append(
                    f"{self.source} {self.relation} {self.target}: source must be element-like"
                )
            if not _carrier_compatible(source.carrier, target.carrier):
                errors.append(
                    f"{self.source} {self.relation} {self.target}: carrier mismatch "
                    f"{source.carrier!r} vs {target.carrier!r}"
                )

        if self.relation in {"subset", "proper_subset", "superset"}:
            if source.kind not in SET_KINDS or target.kind not in SET_KINDS:
                errors.append(
                    f"{self.source} {self.relation} {self.target}: both sides must be set-like"
                )
            if not _carrier_compatible(source.carrier, target.carrier):
                errors.append(
                    f"{self.source} {self.relation} {self.target}: carrier mismatch "
                    f"{source.carrier!r} vs {target.carrier!r}"
                )

        if self.relation == "licenses":
            pair = (self.source, self.target)
            if pair in BLOCKED_LICENSES:
                errors.append(
                    f"{self.source} cannot license {self.target}; authority promotion blocked"
                )
            elif pair not in ALLOWED_LICENSES:
                errors.append(
                    f"{self.source} licenses {self.target}: license path is not admitted"
                )

        return errors


@dataclass(frozen=True)
class MetaLogicContext:
    """Typed meta-layer context for a CAS turn or trace node."""

    objects: list[MetaLogicObject] = field(default_factory=list)
    relations: list[MetaLogicRelation] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "objects": [obj.to_dict() for obj in self.objects],
            "relations": [rel.to_dict() for rel in self.relations],
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.objects:
            errors.append("meta_logic_context must include at least one object")
        if not self.relations:
            errors.append("meta_logic_context must include at least one relation")

        object_map: dict[str, MetaLogicObject] = {}
        for obj in self.objects:
            if obj.name in object_map:
                errors.append(f"duplicate meta-logic object {obj.name!r}")
            object_map[obj.name] = obj
            errors.extend(obj.validate())

        for relation in self.relations:
            errors.extend(relation.validate(object_map))
        return errors


@dataclass(frozen=True)
class CASStateContext:
    """Prior-state facts used by turn-type admissibility predicates."""

    facts: set[str] = field(default_factory=set)

    def to_dict(self) -> dict[str, list[str]]:
        return {"facts": sorted(self.facts)}

    def validate_for_turn_type(self, turn_type: str) -> list[str]:
        required = TURN_PRECONDITIONS.get(turn_type)
        if required is None:
            return [f"unknown turn_type {turn_type!r}"]
        missing = sorted(required - self.facts)
        if missing:
            return [
                f"{turn_type}: missing admissibility precondition(s) {missing}"
            ]
        return []


@dataclass(frozen=True)
class RegisterBinding:
    """Typed v7.7 register multiplicity binding."""

    mode: str
    registers: tuple[str, ...]
    omega_target: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "mode": self.mode,
            "registers": list(self.registers),
        }
        if self.omega_target is not None:
            result["omega_target"] = self.omega_target
        return result

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.mode not in REGISTER_MODES:
            errors.append(f"unknown register binding mode {self.mode!r}")
        if not self.registers:
            errors.append("register binding requires at least one register")
        unknown = sorted(register for register in self.registers if register not in REGISTER_VALUES)
        if unknown:
            errors.append(f"unknown register(s) {unknown}")

        if self.mode == "single" and len(self.registers) != 1:
            errors.append("single register binding requires exactly one register")
        if self.mode == "set_spec" and len(self.registers) < 2:
            errors.append("set_spec register binding requires at least two registers")
        if self.mode == "co_presence" and self.omega_target is not None:
            errors.append("co_presence must not name an emergent omega target")
        if self.mode == "integration":
            if len(self.registers) < 2:
                errors.append("integration requires at least two registers")
            if not self.omega_target:
                errors.append("integration requires omega_target")
        elif self.omega_target and self.mode != "co_presence":
            errors.append(f"{self.mode} must not carry omega_target")
        return errors


@dataclass(frozen=True)
class ProductionIngredient:
    """One typed ingredient in a v7.6 production transition."""

    state: str
    coefficient: float
    available: float

    def to_dict(self) -> dict[str, float | str]:
        return {
            "state": self.state,
            "coefficient": self.coefficient,
            "available": self.available,
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.state:
            errors.append("production ingredient missing state")
        if self.coefficient <= 0:
            errors.append(f"{self.state}: coefficient must be > 0")
        if self.available < 0:
            errors.append(f"{self.state}: available amount must be >= 0")
        return errors


@dataclass(frozen=True)
class ProductionModifier:
    """Catalyst or inhibitor in a v7.6 production transition."""

    kind: str
    primitive: str
    scale: float = 1.0

    def to_dict(self) -> dict[str, float | str]:
        return {
            "kind": self.kind,
            "primitive": self.primitive,
            "scale": self.scale,
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.kind not in {"catalyst", "inhibitor"}:
            errors.append(f"{self.primitive}: modifier kind must be catalyst or inhibitor")
        if not self.primitive:
            errors.append("production modifier missing primitive")
        if self.scale <= 0:
            errors.append(f"{self.primitive}: modifier scale must be > 0")
        if not _looks_like_cas_primitive(self.primitive):
            errors.append(f"{self.primitive}: modifier primitive is not a CAS primitive")
        return errors


@dataclass(frozen=True)
class ProductionTransition:
    """Typed v7.6 production semantics transition."""

    omega_target: str
    ingredients: list[ProductionIngredient]
    limiting_reagent: str
    theoretical_yield: float
    leakage: float = 0.0
    modifiers: list[ProductionModifier] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "omega_target": self.omega_target,
            "ingredients": [ingredient.to_dict() for ingredient in self.ingredients],
            "limiting_reagent": self.limiting_reagent,
            "theoretical_yield": self.theoretical_yield,
            "leakage": self.leakage,
            "modifiers": [modifier.to_dict() for modifier in self.modifiers],
        }

    def validate(self, tolerance: float = 1e-6) -> list[str]:
        errors: list[str] = []
        if not self.omega_target:
            errors.append("production transition missing omega_target")
        if not self.ingredients:
            errors.append("production transition requires at least one ingredient")
        for ingredient in self.ingredients:
            errors.extend(ingredient.validate())
        for modifier in self.modifiers:
            errors.extend(modifier.validate())
        if errors:
            return errors

        ingredient_states = {ingredient.state for ingredient in self.ingredients}
        for modifier in self.modifiers:
            if modifier.primitive in ingredient_states:
                errors.append(
                    f"{modifier.primitive}: catalyst/inhibitor cannot also be an ingredient"
                )

        yields = {
            ingredient.state: ingredient.available / ingredient.coefficient
            for ingredient in self.ingredients
        }
        expected_limiter = min(yields, key=yields.get)
        expected_yield = yields[expected_limiter]
        if self.limiting_reagent != expected_limiter:
            errors.append(
                "limiting_reagent mismatch: "
                f"expected {expected_limiter!r}, got {self.limiting_reagent!r}"
            )
        if abs(self.theoretical_yield - expected_yield) > tolerance:
            errors.append(
                "theoretical_yield mismatch: "
                f"expected {expected_yield:.6g}, got {self.theoretical_yield:.6g}"
            )
        if self.leakage < 0:
            errors.append("production leakage must be >= 0")
        return errors


@dataclass(frozen=True)
class DomainTransition:
    """Typed domain-descent or licensed feedback transition."""

    source_domain: str
    target_domain: str
    transition_type: str = "descent"
    feedback_license: str | None = None

    def to_dict(self) -> dict[str, str]:
        result = {
            "source_domain": self.source_domain,
            "target_domain": self.target_domain,
            "transition_type": self.transition_type,
        }
        if self.feedback_license is not None:
            result["feedback_license"] = self.feedback_license
        return result

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.source_domain not in DOMAINS:
            errors.append(f"unknown source_domain {self.source_domain!r}")
        if self.target_domain not in DOMAINS:
            errors.append(f"unknown target_domain {self.target_domain!r}")
        if errors:
            return errors

        source_index = DOMAINS.index(self.source_domain)
        target_index = DOMAINS.index(self.target_domain)
        if self.transition_type == "descent":
            if target_index < source_index:
                errors.append(
                    f"domain descent cannot move {self.source_domain}->{self.target_domain}"
                )
        elif self.transition_type == "feedback":
            if not (self.source_domain == "O" and self.target_domain == "P"):
                errors.append("feedback transition currently admits only O->P")
            if not self.feedback_license:
                errors.append("feedback transition requires feedback_license")
        else:
            errors.append(f"unknown domain transition_type {self.transition_type!r}")
        return errors


@dataclass(frozen=True)
class CASTransition:
    """Typed transition object proposed before any surface text is rendered."""

    kind: str
    register_binding: RegisterBinding | None = None
    production: ProductionTransition | None = None
    domain_transition: DomainTransition | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"kind": self.kind}
        if self.register_binding is not None:
            result["register_binding"] = self.register_binding.to_dict()
        if self.production is not None:
            result["production"] = self.production.to_dict()
        if self.domain_transition is not None:
            result["domain_transition"] = self.domain_transition.to_dict()
        return result

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.kind:
            errors.append("transition missing kind")
        if self.register_binding is not None:
            errors.extend(self.register_binding.validate())
        if self.production is not None:
            errors.extend(self.production.validate())
        if self.domain_transition is not None:
            errors.extend(self.domain_transition.validate())
        return errors

    def validate_for_zone(self, zone: str) -> list[ValidationDiagnostic]:
        diagnostics: list[ValidationDiagnostic] = []
        if not self.kind:
            diagnostics.append(
                ValidationDiagnostic(
                    "structural",
                    "missing_transition_kind",
                    "transition missing kind",
                    suggestion="emit a concrete transition kind before rendering",
                )
            )
        if self.register_binding is not None:
            diagnostics.extend(
                _diagnostics_from_errors(
                    self.register_binding.validate(),
                    phase="meta_logic",
                    code="register_multiplicity_invalid",
                    suggestion="repair register mode/registers/omega_target",
                )
            )
        if self.production is not None:
            diagnostics.extend(
                _diagnostics_from_errors(
                    self.production.validate(),
                    phase="tight_semantics",
                    code="production_invalid",
                    suggestion="repair recipe coefficients, limiter, yield, or modifiers",
                    severity="error" if zone == "TIGHT" else "warning",
                )
            )
        if self.domain_transition is not None:
            diagnostics.extend(
                _diagnostics_from_errors(
                    self.domain_transition.validate(),
                    phase="tight_semantics",
                    code="domain_transition_invalid",
                    suggestion="repair domain descent/feedback license",
                    severity="error" if zone == "TIGHT" else "warning",
                )
            )
        return diagnostics


@dataclass(frozen=True)
class CASTraceNode:
    """One span-level conversational trace node."""

    node_id: str
    surface_span: str
    turn_type: str
    cas_state: str
    role: str
    meta_logic_context: MetaLogicContext
    state_context: CASStateContext = field(default_factory=CASStateContext)
    transition: CASTransition | None = None
    source_state: str | None = None
    target_state: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "node_id": self.node_id,
            "surface_span": self.surface_span,
            "turn_type": self.turn_type,
            "cas_state": self.cas_state,
            "role": self.role,
            "meta_logic_context": self.meta_logic_context.to_dict(),
            "state_context": self.state_context.to_dict(),
        }
        if self.transition is not None:
            result["transition"] = self.transition.to_dict()
        if self.source_state is not None:
            result["source_state"] = self.source_state
        if self.target_state is not None:
            result["target_state"] = self.target_state
        return result

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.node_id:
            errors.append("trace node missing node_id")
        if not self.surface_span:
            errors.append(f"{self.node_id}: trace node missing surface_span")
        if self.turn_type not in TURN_TYPES:
            errors.append(f"{self.node_id}: unknown turn_type {self.turn_type!r}")
        if not self.cas_state:
            errors.append(f"{self.node_id}: trace node missing cas_state")
        if not self.role:
            errors.append(f"{self.node_id}: trace node missing role")
        errors.extend(
            f"{self.node_id}: {error}"
            for error in self.state_context.validate_for_turn_type(self.turn_type)
        )
        if self.transition is not None:
            errors.extend(
                f"{self.node_id}: {diagnostic.message}"
                for diagnostic in self.transition_diagnostics()
                if diagnostic.severity == "error"
            )
        errors.extend(
            f"{self.node_id}: {error}" for error in self.meta_logic_context.validate()
        )
        return errors

    @property
    def zone(self) -> str:
        if self.turn_type in TIGHT_TURN_TYPES:
            return "TIGHT"
        if self.turn_type in SHELL_TURN_TYPES:
            return "SHELL"
        return "UNKNOWN"

    def transition_diagnostics(self) -> list[ValidationDiagnostic]:
        if self.transition is None:
            return []
        return self.transition.validate_for_zone(self.zone)


@dataclass(frozen=True)
class CASTraceEdge:
    """Typed edge between trace nodes."""

    source: str
    target: str
    relation: str

    def to_dict(self) -> dict[str, str]:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
        }


@dataclass(frozen=True)
class CASTrace:
    """Phase-1 trace DAG: ordered nodes plus typed edges and small indices."""

    nodes: list[CASTraceNode]
    edges: list[CASTraceEdge] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        node_ids: set[str] = set()
        for node in self.nodes:
            if node.node_id in node_ids:
                errors.append(f"duplicate trace node {node.node_id!r}")
            node_ids.add(node.node_id)
            errors.extend(node.validate())
        for edge in self.edges:
            if edge.source not in node_ids:
                errors.append(f"trace edge {edge.source}->{edge.target}: unknown source")
            if edge.target not in node_ids:
                errors.append(f"trace edge {edge.source}->{edge.target}: unknown target")
            if edge.relation not in {"depends_on", "supports", "cites", "licenses", "contains"}:
                errors.append(
                    f"trace edge {edge.source}->{edge.target}: unknown relation {edge.relation!r}"
                )
        errors.extend(_trace_cycle_errors(self.nodes, self.edges))
        return errors

    def query(self) -> "TraceQueryEngine":
        return TraceQueryEngine(self)


class TraceQueryEngine:
    """Bounded typed queries over the Phase-1 trace DAG."""

    def __init__(self, trace: CASTrace) -> None:
        self.trace = trace
        self.by_id = {node.node_id: node for node in trace.nodes}
        self.by_turn_type: dict[str, list[CASTraceNode]] = {}
        self.by_domain: dict[str, list[CASTraceNode]] = {}
        self.in_edges: dict[str, list[CASTraceEdge]] = {}
        self.out_edges: dict[str, list[CASTraceEdge]] = {}
        for node in trace.nodes:
            self.by_turn_type.setdefault(node.turn_type, []).append(node)
            domain = _node_domain(node)
            if domain is not None:
                self.by_domain.setdefault(domain, []).append(node)
        for edge in trace.edges:
            self.out_edges.setdefault(edge.source, []).append(edge)
            self.in_edges.setdefault(edge.target, []).append(edge)

    def nodes_for_turn_type(self, turn_type: str) -> list[CASTraceNode]:
        return list(self.by_turn_type.get(turn_type, []))

    def latest_by_domain(self, domain: str) -> CASTraceNode | None:
        nodes = self.by_domain.get(domain, [])
        return nodes[-1] if nodes else None

    def predecessors(self, node_id: str, relation: str | None = None) -> list[CASTraceNode]:
        edges = self.in_edges.get(node_id, [])
        if relation is not None:
            edges = [edge for edge in edges if edge.relation == relation]
        return [self.by_id[edge.source] for edge in edges if edge.source in self.by_id]

    def has_feedback_license(self, node_id: str, lookback: int = 10) -> bool:
        if node_id not in self.by_id:
            return False
        ordered_ids = [node.node_id for node in self.trace.nodes]
        node_index = ordered_ids.index(node_id)
        window = set(ordered_ids[max(0, node_index - lookback):node_index])
        return any(
            edge.relation == "licenses"
            and edge.target == node_id
            and edge.source in window
            for edge in self.trace.edges
        )


@dataclass(frozen=True)
class CASPerturbationExample:
    """Counterfactual used to test whether CAS state controls token likelihood."""

    perturbation_type: str
    corrupted_field: str
    expected_effect: str
    corrupted_value: str

    def to_dict(self) -> dict[str, str]:
        return {
            "perturbation_type": self.perturbation_type,
            "corrupted_field": self.corrupted_field,
            "expected_effect": self.expected_effect,
            "corrupted_value": self.corrupted_value,
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        for field_name, value in (
            ("perturbation_type", self.perturbation_type),
            ("corrupted_field", self.corrupted_field),
            ("expected_effect", self.expected_effect),
            ("corrupted_value", self.corrupted_value),
        ):
            if not value:
                errors.append(f"perturbation missing {field_name}")
        return errors


@dataclass(frozen=True)
class CASTurnRecord:
    """JSONL-ready CAS Transformer turn record."""

    id: str
    prompt: str
    response: str
    cas_expression: str
    trace: list[CASTraceNode]
    meta_logic_context: MetaLogicContext
    trace_edges: list[CASTraceEdge] = field(default_factory=list)
    compiler: dict[str, Any] = field(default_factory=dict)
    perturbations: list[CASPerturbationExample] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "response": self.response,
            "cas_expression": self.cas_expression,
            "trace": [node.to_dict() for node in self.trace],
            "trace_edges": [edge.to_dict() for edge in self.trace_edges],
            "meta_logic_context": self.meta_logic_context.to_dict(),
            "compiler": dict(self.compiler),
            "perturbations": [item.to_dict() for item in self.perturbations],
            "provenance": dict(self.provenance),
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.id:
            errors.append("record missing id")
        if not self.prompt:
            errors.append(f"{self.id}: record missing prompt")
        if not self.response:
            errors.append(f"{self.id}: record missing response")
        if not self.cas_expression:
            errors.append(f"{self.id}: record missing cas_expression")
        if not self.trace:
            errors.append(f"{self.id}: record must include at least one trace node")

        node_ids: set[str] = set()
        for node in self.trace:
            if node.node_id in node_ids:
                errors.append(f"{self.id}: duplicate trace node {node.node_id!r}")
            node_ids.add(node.node_id)
            errors.extend(f"{self.id}: {error}" for error in node.validate())

        trace_errors = CASTrace(self.trace, self.trace_edges).validate()
        errors.extend(f"{self.id}: {error}" for error in trace_errors)

        errors.extend(
            f"{self.id}: {error}" for error in self.meta_logic_context.validate()
        )
        for perturbation in self.perturbations:
            errors.extend(
                f"{self.id}: {error}" for error in perturbation.validate()
            )
        return errors


def _carrier_compatible(source: str, target: str) -> bool:
    return source == target or source == ANY_CARRIER or target == ANY_CARRIER


def validate_compound_transition(trace: CASTrace) -> list[ValidationDiagnostic]:
    """Three-phase compound transition validation with repair diagnostics."""

    diagnostics: list[ValidationDiagnostic] = []
    node_ids: set[str] = set()

    # Phase 1: structural walk.
    for node in trace.nodes:
        if node.node_id in node_ids:
            diagnostics.append(
                ValidationDiagnostic(
                    "structural",
                    "duplicate_trace_node",
                    f"duplicate trace node {node.node_id!r}",
                    suggestion="emit unique trace_node_id values",
                )
            )
        node_ids.add(node.node_id)
        diagnostics.extend(
            _diagnostics_from_errors(
                [error for error in node.validate() if "meta_logic_context" not in error],
                phase="structural",
                code="trace_node_invalid",
                suggestion="repair trace-node required fields and turn preconditions",
            )
        )

    for edge in trace.edges:
        if edge.source not in node_ids or edge.target not in node_ids:
            diagnostics.append(
                ValidationDiagnostic(
                    "structural",
                    "trace_edge_endpoint_invalid",
                    f"trace edge {edge.source}->{edge.target} references unknown node",
                    suggestion="repair trace edge endpoints",
                )
            )

    # Phase 2: meta-logic/register walk.
    for node in trace.nodes:
        diagnostics.extend(
            _diagnostics_from_errors(
                node.meta_logic_context.validate(),
                phase="meta_logic",
                code="meta_logic_invalid",
                suggestion="repair membership/subset/authority/evidence relations",
            )
        )
        diagnostics.extend(node.transition_diagnostics())

    # Phase 3: graph-level semantics.
    diagnostics.extend(
        _diagnostics_from_errors(
            _trace_cycle_errors(trace.nodes, trace.edges),
            phase="tight_semantics",
            code="trace_cycle",
            suggestion="remove cyclic trace dependency",
        )
    )
    return diagnostics


def _diagnostics_from_errors(
    errors: list[str],
    *,
    phase: str,
    code: str,
    suggestion: str,
    severity: str = "error",
) -> list[ValidationDiagnostic]:
    return [
        ValidationDiagnostic(
            phase,
            code,
            error,
            severity=severity,
            fixable=True,
            suggestion=suggestion,
        )
        for error in errors
    ]


def _looks_like_cas_primitive(value: str) -> bool:
    return value.startswith("^") or value.startswith("Omega_") or value.startswith("Ω_")


def _node_domain(node: CASTraceNode) -> str | None:
    if node.transition and node.transition.domain_transition is not None:
        return node.transition.domain_transition.target_domain
    marker = "^"
    if marker not in node.cas_state:
        return None
    for domain in DOMAINS:
        if f"^{domain}" in node.cas_state:
            return domain
    return None


def _trace_cycle_errors(nodes: list[CASTraceNode], edges: list[CASTraceEdge]) -> list[str]:
    node_ids = {node.node_id for node in nodes}
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    for edge in edges:
        if edge.source in node_ids and edge.target in node_ids:
            adjacency[edge.source].append(edge.target)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> bool:
        if node_id in visiting:
            return True
        if node_id in visited:
            return False
        visiting.add(node_id)
        for child in adjacency.get(node_id, []):
            if visit(child):
                return True
        visiting.remove(node_id)
        visited.add(node_id)
        return False

    for node_id in node_ids:
        if visit(node_id):
            return ["trace graph contains a cycle"]
    return []
