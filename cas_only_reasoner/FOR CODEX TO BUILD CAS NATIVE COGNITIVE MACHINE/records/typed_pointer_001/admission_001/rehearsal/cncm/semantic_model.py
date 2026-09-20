"""Closed v0.4 source-attested correction memory contracts.

Source labels describe provenance, not independently verified world truth.
Memory substitution is a proposal until the coordinator independently checks
the original references, source history, external ingress anchor and receipts.
Placeholder problems are only for planning/bootstrapping; they confer no
permission to execute their substituted zeros. Frozen earlier contracts remain
unchanged and supply the inherited equation, procedure and state checks.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum
import json

from .canonical import canonical_json, digest, to_primitive
from .model import ContractError, ProblemPacket
from .native_model import (NativeBudget, _counter, _identifier, _legacy, _list,
                          _rational, _require, _sha, _typed)
from .nested_model import (Equation, NestedProblem, NestedState, MAX_EQUATIONS,
    MAX_TERMS, MAX_STATE_BYTES, MAX_PROBLEM_BYTES, NESTED_RUNTIME_VERSION,
    NESTED_CONSTITUTION_REVISION, NESTED_STATE_SCHEMA, RESULT_PREDICATE,
    _bounded_json, _decode, _pairs, _wire, create_problem as create_nested_problem)

VERSION = "0.4.0"
CONSTITUTION = "cncm-constitution/semantic-0.4"
STATEMENT_SCHEMA = "cncm.semantic-source-statement/0.4"
REFERENCE_SCHEMA = "cncm.semantic-memory-ref/0.4"
EQUATION_SCHEMA = "cncm.semantic-equation/0.4"
PROBLEM_SCHEMA = "cncm.semantic-problem/0.4"
BINDING_SCHEMA = "cncm.semantic-recall-binding/0.4"
RECORD_SCHEMA = "cncm.semantic-record/0.4"
STATE_SCHEMA = "cncm.semantic-state/0.4"
MAX_STATEMENTS = 256
MAX_REFERENCES = 48
MAX_SEMANTIC_RECORDS = 1024
MAX_SEMANTIC_RECORD_BYTES = 128 * 1024
SOURCE_STATUSES = frozenset({"USER_ATTESTED", "TEST_FIXTURE"})
RECORD_KINDS = frozenset({"STORE", "RECALL", "RESOLUTION", "WORK_RESERVATION"})


class SemanticIntentType(str, Enum):
    STORE_SOURCE = "STORE_SOURCE"
    RECALL_MEMORY = "RECALL_MEMORY"
    CHECK_MEMORY_RESOLUTION = "CHECK_MEMORY_RESOLUTION"


def canonical_trusted_ingress(values):
    """Canonicalize a host-supplied digest tuple without creating its authority."""
    _require(type(values) is tuple and len(values) <= MAX_STATEMENTS, "trusted ingress tuple bound/type invalid")
    for value in values:
        _sha(value, "trusted ingress statement")
    _require(len(set(values)) == len(values), "duplicate trusted ingress digest")
    return tuple(sorted(values))


def ingress_digest(values):
    return digest(list(canonical_trusted_ingress(values)))


@dataclass(frozen=True, slots=True)
class SourceStatement:
    scope: str
    key: str
    source_id: str
    value: str | None
    status: str
    action: str
    previous_digest: str | None
    source_ref: str

    def __post_init__(self):
        _typed(self, SourceStatement)
        for name in ("scope", "key", "source_id"):
            _identifier(getattr(self, name), name)
        _require(self.status in SOURCE_STATUSES, "source status cannot manufacture independent verification")
        _require(self.action in {"ASSERT", "RETRACT"}, "source action invalid")
        _sha(self.previous_digest, "previous statement", optional=True)
        _require(1 <= len(self.source_ref) <= 1024, "source reference text bound invalid")
        if self.action == "ASSERT":
            _rational(self.value)
        else:
            _require(self.value is None, "retraction cannot carry an asserted value")

    @property
    def statement_digest(self):
        return digest(self.to_dict())

    def to_dict(self):
        return {"schema_version": STATEMENT_SCHEMA, **to_primitive(self)}

    @classmethod
    def from_dict(cls, value):
        return cls(**_decode(value, cls, STATEMENT_SCHEMA))


@dataclass(frozen=True, slots=True)
class MemoryRef:
    scope: str
    key: str
    evidence_requirement: str = "ATTESTED"

    def __post_init__(self):
        _typed(self, MemoryRef)
        _identifier(self.scope, "memory scope")
        _identifier(self.key, "memory key")
        _require(self.evidence_requirement in {"ATTESTED", "INDEPENDENTLY_VERIFIED"},
                 "memory evidence requirement invalid")

    @property
    def ref_key(self):
        return self.scope, self.key, self.evidence_requirement

    def to_dict(self):
        return {"schema_version": REFERENCE_SCHEMA, **to_primitive(self)}

    @classmethod
    def from_dict(cls, value):
        return cls(**_decode(value, cls, REFERENCE_SCHEMA))


def _scalar_wire(value):
    return value.to_dict() if type(value) is MemoryRef else value


def _scalar_decode(value):
    if type(value) is dict:
        return MemoryRef.from_dict(value)
    _require(type(value) is str, "semantic scalar must be rational text or typed reference")
    _rational(value)
    return value


@dataclass(frozen=True, slots=True)
class SemanticEquation:
    variable: str
    a: str | MemoryRef
    b: str | MemoryRef
    constant: str | MemoryRef = "0"
    terms: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        _typed(self, SemanticEquation)
        for value in (self.a, self.b, self.constant):
            if type(value) is str:
                _rational(value)
        # Reuse the exact finite equation grammar without assigning the unknown
        # reference values any mathematical truth or execution permission.
        self.placeholder_equation()

    @property
    def dependencies(self):
        return tuple(name for name, _ in self.terms)

    def placeholder_equation(self):
        return Equation(self.variable, self.a if type(self.a) is str else "0",
                        self.b if type(self.b) is str else "0",
                        self.constant if type(self.constant) is str else "0", self.terms)

    def to_dict(self):
        return {"schema_version": EQUATION_SCHEMA, "variable": self.variable,
                "a": _scalar_wire(self.a), "b": _scalar_wire(self.b),
                "constant": _scalar_wire(self.constant), "terms": [list(row) for row in self.terms]}

    @classmethod
    def from_dict(cls, value):
        body = _decode(value, cls, EQUATION_SCHEMA)
        for name in ("a", "b", "constant"):
            body[name] = _scalar_decode(body[name])
        body["terms"] = _pairs(body["terms"], "semantic terms", MAX_TERMS)
        return cls(**body)


@dataclass(frozen=True, slots=True)
class RecallBinding:
    ref: MemoryRef
    value: str
    statement_digests: tuple[str, ...]
    statuses: tuple[str, ...]
    receipt_digest: str

    def __post_init__(self):
        _typed(self, RecallBinding)
        _rational(self.value)
        _require(1 <= len(self.statement_digests) <= MAX_STATEMENTS
                 and self.statement_digests == tuple(sorted(set(self.statement_digests))),
                 "binding statement digests must be bounded, sorted and unique")
        for value in self.statement_digests:
            _sha(value, "binding statement")
        _require(len(self.statuses) == len(self.statement_digests)
                 and all(status in SOURCE_STATUSES for status in self.statuses),
                 "binding statuses must describe each source without invented verification")
        _sha(self.receipt_digest, "recall receipt")
        # A stronger requested evidence level is preserved, not granted here.
        # The independent verifier rejects a binding whose evidence is weaker.

    def to_dict(self):
        return {"schema_version": BINDING_SCHEMA, "ref": self.ref.to_dict(), "value": self.value,
                "statement_digests": list(self.statement_digests), "statuses": list(self.statuses),
                "receipt_digest": self.receipt_digest}

    @classmethod
    def from_dict(cls, value):
        body = _decode(value, cls, BINDING_SCHEMA)
        body["ref"] = MemoryRef.from_dict(body["ref"])
        for name in ("statement_digests", "statuses"):
            _list(body[name], name, MAX_STATEMENTS)
            body[name] = tuple(body[name])
        return cls(**body)


@dataclass(frozen=True, slots=True)
class SemanticProblem:
    reasoning: ProblemPacket
    equations: tuple[SemanticEquation, ...]
    query_variable: str
    budget: NativeBudget = NativeBudget()
    updates: tuple[SourceStatement, ...] = ()

    def __post_init__(self):
        _typed(self, SemanticProblem)
        _require(len(self.equations) <= MAX_EQUATIONS, "semantic equation count bound exceeded")
        _require(len(self.updates) <= MAX_STATEMENTS, "semantic update count bound exceeded")
        _require(len({row.statement_digest for row in self.updates}) == len(self.updates), "duplicate semantic update")
        # This validates reserved predicates, entity declarations, budgets and
        # duplicate equation producers while retaining missing/cyclic references.
        self.placeholder_problem()
        _require(len(self.references) <= MAX_REFERENCES, "semantic reference count bound exceeded")
        _bounded_json(self.to_dict(), MAX_PROBLEM_BYTES, "semantic problem")

    def equation_map(self):
        return {row.variable: row for row in self.equations}

    def reachable_variables(self):
        equations, seen, pending = self.equation_map(), set(), [self.query_variable]
        while pending:
            variable = pending.pop()
            if variable in seen:
                continue
            seen.add(variable)
            equation = equations.get(variable)
            if equation is not None:
                pending.extend(equation.dependencies)
        return frozenset(seen)

    @property
    def references(self):
        reachable = self.reachable_variables()
        refs = {value for row in self.equations if row.variable in reachable
                for value in (row.a, row.b, row.constant) if type(value) is MemoryRef}
        return tuple(sorted(refs, key=lambda ref: ref.ref_key))

    @property
    def input_hash(self):
        return digest(self.to_dict())

    @property
    def result_key(self):
        return self.reasoning.query.key

    def placeholder_problem(self):
        """Numeric zeros for boot/planning only, never a resolved execution grant."""
        return NestedProblem(self.reasoning, self.query_variable,
            tuple(row.placeholder_equation() for row in self.equations), self.budget)

    def resolved_problem(self, bindings):
        """Propose numeric substitution; a separate verifier must admit it.

        Every reachable reference needs exactly one binding. Only reachable
        equations enter the numeric problem, in their original tuple order.
        The original semantic problem retains all omitted templates and binds
        them in its input hash. Missing producers and cycles stay diagnosable.
        """
        _require(type(bindings) is tuple and len(bindings) <= MAX_REFERENCES
                 and all(type(row) is RecallBinding for row in bindings), "typed bounded recall bindings required")
        for row in bindings:
            RecallBinding.from_dict(row.to_dict())
        by_ref = {row.ref: row for row in bindings}
        _require(len(by_ref) == len(bindings), "duplicate recall binding")
        _require(set(by_ref) == set(self.references), "reachable memory references are unresolved or binding scope is foreign")
        reachable = self.reachable_variables()
        equations = []
        for row in self.equations:
            if row.variable not in reachable:
                continue
            def substitute(value):
                if type(value) is str:
                    return value
                return by_ref[value].value
            equations.append(Equation(row.variable, substitute(row.a), substitute(row.b),
                                      substitute(row.constant), row.terms))
        return NestedProblem(self.reasoning, self.query_variable, tuple(equations), self.budget)

    def to_dict(self):
        return {"schema_version": PROBLEM_SCHEMA, "reasoning": self.reasoning.to_dict(),
                "equations": [row.to_dict() for row in sorted(self.equations, key=lambda row: row.variable)],
                "query_variable": self.query_variable, "budget": self.budget.to_dict(),
                "updates": [row.to_dict() for row in self.updates]}

    @classmethod
    def from_dict(cls, value):
        body = _decode(value, cls, PROBLEM_SCHEMA)
        _bounded_json(value, MAX_PROBLEM_BYTES, "semantic problem")
        _list(body["equations"], "semantic equations", MAX_EQUATIONS)
        _list(body["updates"], "semantic updates", MAX_STATEMENTS)
        return cls(_legacy(body["reasoning"], ProblemPacket),
            tuple(SemanticEquation.from_dict(row) for row in body["equations"]), body["query_variable"],
            NativeBudget.from_dict(body["budget"]), tuple(SourceStatement.from_dict(row) for row in body["updates"]))


def create_problem(equations, query_variable, problem_id="semantic-equations", goal_id="goal-semantic",
                   budget=NativeBudget(), updates=(), max_ticks=128, rpm_depth_limit=8):
    _require(type(equations) is tuple and len(equations) <= MAX_EQUATIONS
             and all(type(row) is SemanticEquation for row in equations), "typed semantic equation tuple required")
    base = create_nested_problem(tuple(row.placeholder_equation() for row in equations), query_variable,
        problem_id=problem_id, goal_id=goal_id, budget=budget, max_ticks=max_ticks, rpm_depth_limit=rpm_depth_limit)
    return SemanticProblem(base.reasoning, equations, query_variable, budget, updates)


@dataclass(frozen=True, slots=True)
class SemanticRecord:
    kind: str
    body_json: str
    record_digest: str

    def __post_init__(self):
        _require(type(self.kind) is str and self.kind in RECORD_KINDS, "unknown semantic record kind")
        _require(type(self.body_json) is str and len(self.body_json) <= MAX_SEMANTIC_RECORD_BYTES,
                 "semantic record text bound exceeded")
        _require(len(self.body_json.encode()) <= MAX_SEMANTIC_RECORD_BYTES, "semantic record byte bound exceeded")
        try:
            body = json.loads(self.body_json)
        except (ValueError, RecursionError) as exc:
            raise ContractError("semantic record JSON invalid") from exc
        _require(type(body) is dict, "semantic record body must be an object")
        _wire(body)
        _require(canonical_json(body) == self.body_json, "semantic record JSON is not canonical")
        _sha(self.record_digest, "semantic record")
        _require(self.record_digest == digest({"schema_version": RECORD_SCHEMA, "kind": self.kind, "body": body}),
                 "semantic record digest mismatch")

    @classmethod
    def create(cls, kind, body):
        _require(type(kind) is str and kind in RECORD_KINDS, "unknown semantic record kind")
        _require(type(body) is dict, "semantic record body must be an object")
        encoded = _bounded_json(body, MAX_SEMANTIC_RECORD_BYTES, "semantic record")
        return cls(kind, encoded, digest({"schema_version": RECORD_SCHEMA, "kind": kind, "body": body}))

    def body_dict(self):
        return json.loads(self.body_json)

    def to_dict(self):
        return {"schema_version": RECORD_SCHEMA, **to_primitive(self)}

    @classmethod
    def from_dict(cls, value):
        return cls(**_decode(value, cls, RECORD_SCHEMA))


@dataclass(frozen=True, slots=True, kw_only=True)
class SemanticState(NestedState):
    memory_statements: tuple[SourceStatement, ...] = ()
    memory_bindings: tuple[RecallBinding, ...] = ()
    memory_update_index: int = 0
    memory_failure: str | None = None
    ingress_digest: str
    semantic_records: tuple[SemanticRecord, ...] = ()
    memory_resolution_digest: str | None = None

    def __post_init__(self):
        # Do not invoke NestedState.__post_init__ on this subclass: its exact
        # version contract deliberately rejects 0.4. Validate a separate plain
        # 0.3 view of inherited fields, never use that view as runtime state.
        _typed(self, SemanticState)
        _require(self.runtime_version == VERSION and self.constitution_revision == CONSTITUTION,
                 "semantic state version invalid")
        inherited = {field.name: getattr(self, field.name) for field in fields(NestedState)}
        inherited.update(runtime_version=NESTED_RUNTIME_VERSION, constitution_revision=NESTED_CONSTITUTION_REVISION)
        NestedState(**inherited)
        _require(len(self.memory_statements) <= MAX_STATEMENTS and len(self.memory_bindings) <= MAX_REFERENCES
                 and len(self.semantic_records) <= MAX_SEMANTIC_RECORDS, "semantic state collection bound exceeded")
        _require(len({row.statement_digest for row in self.memory_statements}) == len(self.memory_statements),
                 "duplicate retained source statement")
        _require(len({row.ref for row in self.memory_bindings}) == len(self.memory_bindings), "duplicate retained memory reference")
        _require(len({row.record_digest for row in self.semantic_records}) == len(self.semantic_records),
                 "duplicate retained semantic record")
        _counter(self.memory_update_index, "memory update index", MAX_STATEMENTS)
        if self.memory_failure is not None:
            _identifier(self.memory_failure, "memory failure")
        _sha(self.ingress_digest, "trusted ingress")
        _sha(self.memory_resolution_digest, "memory resolution", optional=True)
        _bounded_json(self.to_dict(), MAX_STATE_BYTES, "semantic state")

    def to_dict(self):
        body = NestedState.to_dict(self)
        body.update(schema_version=STATE_SCHEMA,
            memory_statements=[row.to_dict() for row in self.memory_statements],
            memory_bindings=[row.to_dict() for row in self.memory_bindings],
            semantic_records=[row.to_dict() for row in self.semantic_records])
        return body

    @classmethod
    def from_dict(cls, value):
        body = _decode(value, cls, STATE_SCHEMA)
        _bounded_json(value, MAX_STATE_BYTES, "semantic state")
        _require(body["runtime_version"] == VERSION and body["constitution_revision"] == CONSTITUTION,
                 "semantic state version invalid")
        for name, maximum in (("memory_statements", MAX_STATEMENTS), ("memory_bindings", MAX_REFERENCES),
                              ("semantic_records", MAX_SEMANTIC_RECORDS)):
            _list(body[name], name, maximum)
        inherited = {field.name: body[field.name] for field in fields(NestedState)}
        inherited.update(schema_version=NESTED_STATE_SCHEMA, runtime_version=NESTED_RUNTIME_VERSION,
                         constitution_revision=NESTED_CONSTITUTION_REVISION)
        inherited["state_hash"] = digest({key: item for key, item in inherited.items() if key not in {"state_hash", "trace_head"}})
        parsed = NestedState.from_dict(inherited)
        restored = {field.name: getattr(parsed, field.name) for field in fields(NestedState)}
        restored.update(runtime_version=body["runtime_version"], constitution_revision=body["constitution_revision"],
                        state_hash=body["state_hash"])
        result = cls(**restored,
            memory_statements=tuple(SourceStatement.from_dict(row) for row in body["memory_statements"]),
            memory_bindings=tuple(RecallBinding.from_dict(row) for row in body["memory_bindings"]),
            memory_update_index=body["memory_update_index"], memory_failure=body["memory_failure"],
            ingress_digest=body["ingress_digest"],
            semantic_records=tuple(SemanticRecord.from_dict(row) for row in body["semantic_records"]),
            memory_resolution_digest=body["memory_resolution_digest"])
        _require(result.state_hash == result.computed_hash(), "semantic state hash mismatch")
        _require(canonical_json(result.to_dict()) == canonical_json(value), "semantic state roundtrip mismatch")
        return result
