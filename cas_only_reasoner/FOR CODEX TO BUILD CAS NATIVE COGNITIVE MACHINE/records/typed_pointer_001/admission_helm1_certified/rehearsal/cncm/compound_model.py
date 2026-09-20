"""Closed v0.5 nested-affine problem and acquisition-state contracts.

The input family is exactly a*(b*x+c)+d=e. A problem supplies its five original
parameters, never an execution graph, learned program or answer. Memory labels
remain source attestations. Parsing program/state bytes establishes structure
and identity only; the coordinator must reconstruct qualification, exact-call
checking, source authorization and history before using retained procedures.
Frozen earlier models are validated through separate versioned views.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum
import json

from .canonical import canonical_json, digest, to_primitive
from .compound_program import CallProgram
from .model import ContractError, ProblemPacket
from .native_model import (NativeBudget, _counter, _identifier, _keys, _legacy,
                          _list, _rational, _require, _sha, _typed)
from .nested_model import NestedProblem, create_problem as create_nested_problem
from .semantic_model import (MemoryRef, RecallBinding, SemanticState, SourceStatement,
    MAX_REFERENCES, MAX_STATEMENTS, VERSION as SEMANTIC_VERSION,
    CONSTITUTION as SEMANTIC_CONSTITUTION, STATE_SCHEMA as SEMANTIC_STATE_SCHEMA)

VERSION = "0.5.0"
CONSTITUTION = "cncm-constitution/compound-0.5"
COMPOUND_CAPABILITY = "cncm.solve-nested-affine/0.1"
PROBLEM_SCHEMA = "cncm.compound-problem/0.5"
CALL_SCHEMA = "cncm.compound-call/0.5"
FRAME_SCHEMA = "cncm.compound-frame/0.5"
RECORD_SCHEMA = "cncm.compound-record/0.5"
STATE_SCHEMA = "cncm.compound-state/0.5"
PARAMETERS = ("a", "b", "c", "d", "e")
MAX_ARTIFACTS = 8
MAX_DEPTH = 8
MAX_RECORDS = 1024
MAX_RECORD_BYTES = 1024 * 1024
MAX_STATE_BYTES = 8 * 1024 * 1024
MAX_PROBLEM_BYTES = 1024 * 1024
DEFAULT_BUDGET = NativeBudget(100000, 10000)
RECORD_KINDS = frozenset({"WORK_RESERVATION", "PRIMITIVE_SELECTION", "PRIMITIVE_INSTALLATION",
    "CONSTRUCTION", "QUALIFICATION", "INSTALLATION", "RETURN", "EXECUTION", "FAILURE", "ROLLBACK"})


class CompoundIntentType(str, Enum):
    REQUEST_COMPOUND = "REQUEST_COMPOUND"
    PUSH_COMPOUND_ACQUISITION = "PUSH_COMPOUND_ACQUISITION"
    PUSH_PRIMITIVE_ACQUISITION = "PUSH_PRIMITIVE_ACQUISITION"
    SELECT_PRIMITIVE = "SELECT_PRIMITIVE"
    INSTALL_PRIMITIVE = "INSTALL_PRIMITIVE"
    RETURN_PRIMITIVE = "RETURN_PRIMITIVE"
    CONSTRUCT_COMPOUND = "CONSTRUCT_COMPOUND"
    INSTALL_COMPOUND = "INSTALL_COMPOUND"
    RETURN_COMPOUND = "RETURN_COMPOUND"
    APPLY_COMPOUND = "APPLY_COMPOUND"
    FAIL_COMPOUND = "FAIL_COMPOUND"
    ROLLBACK_COMPOUND = "ROLLBACK_COMPOUND"
    ROLLBACK_PRIMITIVE = "ROLLBACK_PRIMITIVE"


def _wire(value):
    """Own bounded JSON scanner; frozen record/string limits are not widened."""
    pending, count = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        _require(count <= 100000 and depth <= 40, "compound JSON structure bound exceeded")
        if type(item) is dict:
            _require(len(item) <= 4096 and all(type(key) is str for key in item), "compound JSON object invalid")
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            _require(len(item) <= 4096, "compound JSON list bound exceeded")
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            _require(len(item) <= MAX_RECORD_BYTES, "compound JSON string bound exceeded")
        elif type(item) is int:
            _require(item.bit_length() <= 512, "compound JSON integer bound exceeded")
        else:
            _require(item is None or type(item) is bool, "compound JSON primitive invalid")


def _bounded_json(value, maximum, label):
    _wire(value)
    pending, text_size = [value], 0
    while pending:
        item = pending.pop()
        if type(item) is str:
            text_size += len(item)
        elif type(item) is dict:
            text_size += sum(len(key) for key in item)
            pending.extend(item.values())
        elif type(item) is list:
            pending.extend(item)
        _require(text_size <= maximum, label + " aggregate text bound exceeded")
    encoded = canonical_json(value)
    _require(len(encoded.encode()) <= maximum, label + " byte bound exceeded")
    return encoded


def _decode(value, kind, schema):
    _keys(value, {field.name for field in fields(kind)} | {"schema_version"}, kind.__name__)
    _wire(value)
    _require(type(value["schema_version"]) is str and value["schema_version"] == schema,
             kind.__name__ + " version invalid")
    return {key: item for key, item in value.items() if key != "schema_version"}


def _pairs(value, label):
    _list(value, label, 5)
    _require(all(type(row) is list and len(row) == 2 for row in value), label + " pairs invalid")
    return tuple(tuple(row) for row in value)


def _parameter_tuple(value, *, references):
    _require(type(value) is tuple and len(value) == 5
             and all(type(row) is tuple and len(row) == 2 for row in value)
             and tuple(row[0] for row in value) == PARAMETERS, "exact sorted a..e parameters required")
    for _, scalar in value:
        if references and type(scalar) is MemoryRef:
            MemoryRef.from_dict(scalar.to_dict())
        else:
            _rational(scalar)


@dataclass(frozen=True, slots=True)
class CompoundProblem:
    reasoning: ProblemPacket
    variable: str
    parameters: tuple[tuple[str, str | MemoryRef], ...]
    budget: NativeBudget = DEFAULT_BUDGET
    updates: tuple[SourceStatement, ...] = ()
    construction_limit: int = 420

    def __post_init__(self):
        _typed(self, CompoundProblem)
        _parameter_tuple(self.parameters, references=True)
        _counter(self.construction_limit, "compound construction limit", 420)
        _require(self.construction_limit >= 1, "compound construction limit must be positive")
        _require(len(self.updates) <= MAX_STATEMENTS, "compound source update bound exceeded")
        _require(len({row.statement_digest for row in self.updates}) == len(self.updates), "duplicate compound source update")
        # Only the reasoning guards are reused; no numeric equation or execution
        # graph is introduced into the original compound problem.
        NestedProblem(self.reasoning, self.variable, (), self.budget)
        _bounded_json(self.to_dict(), MAX_PROBLEM_BYTES, "compound problem")

    @property
    def query_variable(self):
        return self.variable

    @property
    def references(self):
        return tuple(sorted({value for _, value in self.parameters if type(value) is MemoryRef},
                            key=lambda ref: ref.ref_key))

    def parameters_dict(self):
        return dict(self.parameters)

    def resolved_inputs(self, bindings):
        _require(type(bindings) is tuple and len(bindings) <= MAX_REFERENCES
                 and all(type(row) is RecallBinding for row in bindings), "typed bounded recall bindings required")
        for row in bindings:
            RecallBinding.from_dict(row.to_dict())
        by_ref = {row.ref: row.value for row in bindings}
        _require(len(by_ref) == len(bindings) and set(by_ref) == set(self.references),
                 "compound memory references unresolved, duplicated or foreign")
        return {name: by_ref[value] if type(value) is MemoryRef else value for name, value in self.parameters}

    @property
    def input_hash(self):
        return digest(self.to_dict())

    @property
    def result_key(self):
        return self.reasoning.query.key

    def to_dict(self):
        return {"schema_version": PROBLEM_SCHEMA, "reasoning": self.reasoning.to_dict(),
            "variable": self.variable, "parameters": [[name, value.to_dict() if type(value) is MemoryRef else value]
                                                       for name, value in self.parameters],
            "budget": self.budget.to_dict(), "updates": [row.to_dict() for row in self.updates],
            "construction_limit": self.construction_limit}

    @classmethod
    def from_dict(cls, value):
        body = _decode(value, cls, PROBLEM_SCHEMA)
        _bounded_json(value, MAX_PROBLEM_BYTES, "compound problem")
        parameters = tuple((name, MemoryRef.from_dict(scalar) if type(scalar) is dict else scalar)
                           for name, scalar in _pairs(body["parameters"], "compound parameters"))
        _list(body["updates"], "compound updates", MAX_STATEMENTS)
        return cls(_legacy(body["reasoning"], ProblemPacket), body["variable"], parameters,
                   NativeBudget.from_dict(body["budget"]), tuple(SourceStatement.from_dict(row) for row in body["updates"]),
                   body["construction_limit"])


def create_problem(parameters, variable="x", problem_id="compound-equation", goal_id="goal-compound",
                   budget=DEFAULT_BUDGET, updates=(), max_ticks=128, rpm_depth_limit=8, construction_limit=420):
    _keys(parameters, PARAMETERS, "compound parameters")
    base = create_nested_problem((), variable, problem_id=problem_id, goal_id=goal_id,
        budget=budget, max_ticks=max_ticks, rpm_depth_limit=rpm_depth_limit)
    return CompoundProblem(base.reasoning, variable, tuple((name, parameters[name]) for name in PARAMETERS),
                           budget, updates, construction_limit)


@dataclass(frozen=True, slots=True)
class CompoundCall:
    call_id: str
    goal_id: str
    variable: str
    inputs: tuple[tuple[str, str], ...]
    status: str = "NEW"
    artifact_sha256: str | None = None
    output: str | None = None
    execution_digest: str | None = None
    failure: str | None = None

    def __post_init__(self):
        _typed(self, CompoundCall)
        for name in ("call_id", "goal_id", "variable"):
            _identifier(getattr(self, name), name)
        _parameter_tuple(self.inputs, references=False)
        _require(self.status in {"NEW", "WAITING", "READY", "COMPLETE", "FAILED"}, "compound call status invalid")
        _sha(self.artifact_sha256, "compound artifact", optional=True)
        _sha(self.execution_digest, "compound execution", optional=True)
        if self.status in {"NEW", "WAITING"}:
            _require(self.artifact_sha256 is None, "pending compound call cannot pin an artifact")
        if self.status in {"READY", "COMPLETE"}:
            _require(self.artifact_sha256 is not None, "ready compound call requires an artifact")
        if self.status == "COMPLETE":
            _rational(self.output, bits=512)
            _require(self.execution_digest is not None and self.failure is None, "complete compound call lacks checked execution")
        else:
            _require(self.output is None and self.execution_digest is None, "unfinished compound call cannot store an answer")
        if self.status == "FAILED":
            _identifier(self.failure, "compound failure")
        else:
            _require(self.failure is None, "nonfailed compound call cannot carry failure")

    def inputs_dict(self):
        return dict(self.inputs)

    @property
    def inputs_digest(self):
        return digest(self.inputs_dict())

    @property
    def call_digest(self):
        return digest(self.to_dict())

    def to_dict(self):
        return {"schema_version": CALL_SCHEMA, **to_primitive(self)}

    @classmethod
    def from_dict(cls, value):
        body = _decode(value, cls, CALL_SCHEMA)
        body["inputs"] = _pairs(body["inputs"], "compound call inputs")
        return cls(**body)


@dataclass(frozen=True, slots=True)
class CompoundFrame:
    frame_id: str
    kind: str
    goal_id: str
    parent_goal_id: str
    call_id: str
    parent_call_digest: str
    parent_branch_digest: str
    return_address: str
    resume_stage: str
    depth: int
    entry_instruction_budget: int
    entry_checker_budget: int

    def __post_init__(self):
        _typed(self, CompoundFrame)
        for name in ("frame_id", "goal_id", "parent_goal_id", "call_id"):
            _identifier(getattr(self, name), name)
        _sha(self.parent_call_digest, "parent compound call")
        _sha(self.parent_branch_digest, "parent compound branch")
        _require(self.kind in {"ACQUIRE_COMPOUND", "ACQUIRE_PRIMITIVE"}, "compound frame kind invalid")
        suffix, stage = ("compound", "COMPOUND_APPLY") if self.kind == "ACQUIRE_COMPOUND" else ("primitive", "COMPOUND_CONSTRUCT")
        _require(self.return_address == f"call:{self.call_id}:{suffix}" and self.resume_stage == stage,
                 "compound frame continuation scope invalid")
        _counter(self.depth, "compound frame depth", MAX_DEPTH)
        _require(self.depth >= 1, "compound frame depth must be positive")
        NativeBudget(self.entry_instruction_budget, self.entry_checker_budget)

    def to_dict(self):
        return {"schema_version": FRAME_SCHEMA, **to_primitive(self)}

    @classmethod
    def from_dict(cls, value):
        return cls(**_decode(value, cls, FRAME_SCHEMA))


@dataclass(frozen=True, slots=True)
class CompoundRecord:
    kind: str
    body_json: str
    record_digest: str

    def __post_init__(self):
        _typed(self, CompoundRecord)
        _require(self.kind in RECORD_KINDS, "unknown compound record kind")
        _require(len(self.body_json) <= MAX_RECORD_BYTES and len(self.body_json.encode()) <= MAX_RECORD_BYTES,
                 "compound record byte bound exceeded")
        try:
            body = json.loads(self.body_json)
        except (ValueError, RecursionError) as exc:
            raise ContractError("compound record JSON invalid") from exc
        _require(type(body) is dict, "compound record body must be object")
        _wire(body)
        _require(canonical_json(body) == self.body_json, "compound record JSON not canonical")
        _sha(self.record_digest, "compound record")
        _require(self.record_digest == digest({"schema_version": RECORD_SCHEMA, "kind": self.kind, "body": body}),
                 "compound record digest mismatch")

    @classmethod
    def create(cls, kind, body):
        _require(type(kind) is str and kind in RECORD_KINDS and type(body) is dict, "compound record kind/body invalid")
        text = _bounded_json(body, MAX_RECORD_BYTES, "compound record")
        return cls(kind, text, digest({"schema_version": RECORD_SCHEMA, "kind": kind, "body": body}))

    def body_dict(self):
        return json.loads(self.body_json)

    def to_dict(self):
        return {"schema_version": RECORD_SCHEMA, **to_primitive(self)}

    @classmethod
    def from_dict(cls, value):
        return cls(**_decode(value, cls, RECORD_SCHEMA))


@dataclass(frozen=True, slots=True, kw_only=True)
class CompoundState(SemanticState):
    rpm_stack: tuple[CompoundFrame, ...]
    compound_call: CompoundCall | None = None
    compound_artifacts: tuple[CallProgram, ...] = ()
    compound_head: str | None = None
    compound_records: tuple[CompoundRecord, ...] = ()

    def __post_init__(self):
        _typed(self, CompoundState)
        _require(self.runtime_version == VERSION and self.constitution_revision == CONSTITUTION,
                 "compound state version invalid")
        inherited = {field.name: getattr(self, field.name) for field in fields(SemanticState)}
        inherited.update(runtime_version=SEMANTIC_VERSION, constitution_revision=SEMANTIC_CONSTITUTION, rpm_stack=())
        SemanticState(**inherited)
        _require(not self.native_calls, "compound state cannot contain nested equation calls")
        _require(len(self.rpm_stack) <= MAX_DEPTH and len(self.compound_artifacts) <= MAX_ARTIFACTS
                 and len(self.compound_records) <= MAX_RECORDS, "compound state collection bound exceeded")
        _require(len({frame.frame_id for frame in self.rpm_stack}) == len(self.rpm_stack), "duplicate compound frame")
        _require(len({row.record_digest for row in self.compound_records}) == len(self.compound_records), "duplicate compound record")
        artifacts = {row.artifact_sha256 for row in self.compound_artifacts}
        _require(len(artifacts) == len(self.compound_artifacts), "duplicate compound artifact")
        primitives = {row.artifact_sha256 for row in self.procedural_artifacts}
        _require(all(row.primitive_sha256 in primitives for row in self.compound_artifacts),
                 "compound artifact references absent primitive")
        _sha(self.compound_head, "compound head", optional=True)
        _require(self.compound_head is None or self.compound_head in artifacts, "compound head references absent artifact")
        _require(self.compound_call is None or self.compound_call.artifact_sha256 is None
                 or self.compound_call.artifact_sha256 in artifacts, "compound call pin references absent artifact")
        _bounded_json(self.to_dict(), MAX_STATE_BYTES, "compound state")

    def to_dict(self):
        body = SemanticState.to_dict(self)
        body.update(schema_version=STATE_SCHEMA, rpm_stack=[row.to_dict() for row in self.rpm_stack],
            compound_call=self.compound_call.to_dict() if self.compound_call is not None else None,
            compound_artifacts=[row.to_dict() for row in self.compound_artifacts],
            compound_records=[row.to_dict() for row in self.compound_records])
        return body

    @classmethod
    def from_dict(cls, value):
        body = _decode(value, cls, STATE_SCHEMA)
        _bounded_json(value, MAX_STATE_BYTES, "compound state")
        _require(body["runtime_version"] == VERSION and body["constitution_revision"] == CONSTITUTION,
                 "compound state version invalid")
        for name, maximum in (("rpm_stack", MAX_DEPTH), ("compound_artifacts", MAX_ARTIFACTS), ("compound_records", MAX_RECORDS)):
            _list(body[name], name, maximum)
        inherited = {field.name: body[field.name] for field in fields(SemanticState)}
        inherited.update(schema_version=SEMANTIC_STATE_SCHEMA, runtime_version=SEMANTIC_VERSION,
                         constitution_revision=SEMANTIC_CONSTITUTION, rpm_stack=[])
        inherited["state_hash"] = digest({key: item for key, item in inherited.items() if key not in {"state_hash", "trace_head"}})
        parsed = SemanticState.from_dict(inherited)
        restored = {field.name: getattr(parsed, field.name) for field in fields(SemanticState)}
        restored.update(runtime_version=body["runtime_version"], constitution_revision=body["constitution_revision"],
                        state_hash=body["state_hash"], rpm_stack=tuple(CompoundFrame.from_dict(row) for row in body["rpm_stack"]))
        result = cls(**restored,
            compound_call=CompoundCall.from_dict(body["compound_call"]) if body["compound_call"] is not None else None,
            compound_artifacts=tuple(CallProgram.from_dict(row) for row in body["compound_artifacts"]),
            compound_head=body["compound_head"],
            compound_records=tuple(CompoundRecord.from_dict(row) for row in body["compound_records"]))
        _require(result.state_hash == result.computed_hash(), "compound state hash mismatch")
        _require(canonical_json(result.to_dict()) == canonical_json(value), "compound state roundtrip mismatch")
        return result
