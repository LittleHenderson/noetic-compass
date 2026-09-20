"""Closed 0.6 proof-backed, conditional result memory contracts.

Structural decoding establishes no authority. Only coordinator replay under
external genesis and ingress can establish admission and continuation lineage.
"""
from dataclasses import dataclass, fields, replace
from enum import Enum
import json

from .canonical import canonical_json, digest, to_primitive
from .model import ContractError, ProblemPacket
from .native_model import NativeBudget, _identifier, _rational, _sha
from .semantic_model import MemoryRef, SourceStatement
from .compound_model import (CompoundProblem, CompoundState, CompoundFrame,
    create_problem as compound_problem, _bounded_json, _decode,
    VERSION as OLD_VERSION, CONSTITUTION as OLD_CONSTITUTION,
    STATE_SCHEMA as OLD_STATE_SCHEMA, DEFAULT_BUDGET)

VERSION = '0.6.0'
CONSTITUTION = 'cncm-constitution/derived-0.6'
REFERENCE_SCHEMA = 'cncm.derived-result-ref/0.6'
DEFINITION_SCHEMA = 'cncm.derived-definition/0.6'
PROBLEM_SCHEMA = 'cncm.derived-problem/0.6'
FRAME_SCHEMA = 'cncm.derived-frame/0.6'
RECORD_SCHEMA = 'cncm.derived-record/0.6'
STATE_SCHEMA = 'cncm.derived-state/0.6'
MAX_MEMORIES = 128
MAX_RECORDS = 1024
MAX_DEPTH = 8


def require(condition, reason):
    if not condition:
        raise ContractError(reason)


class DerivedIntentType(str, Enum):
    REGISTER_DEFINITION = 'REGISTER_DEFINITION'
    INSPECT_DERIVED = 'INSPECT_DERIVED'
    PUSH_DERIVED = 'PUSH_DERIVED'
    GENERATE_DERIVED = 'GENERATE_DERIVED'
    CHECK_DERIVED = 'CHECK_DERIVED'
    ADMIT_DERIVED = 'ADMIT_DERIVED'
    RETURN_DERIVED = 'RETURN_DERIVED'
    STORE_DERIVED = 'STORE_DERIVED'
    FAIL_DERIVED = 'FAIL_DERIVED'


@dataclass(frozen=True, slots=True)
class DerivedResultRef:
    scope: str
    key: str
    evidence_requirement: str = 'CHECKED_FORMAL_DERIVATION'

    def __post_init__(self):
        require(type(self) is DerivedResultRef, 'exact derived reference required')
        _identifier(self.scope, 'derived scope'); _identifier(self.key, 'derived key')
        require(self.evidence_requirement == 'CHECKED_FORMAL_DERIVATION', 'derived evidence requirement invalid')

    @property
    def ref_key(self):
        return self.scope, self.key

    def to_dict(self):
        return {'schema_version': REFERENCE_SCHEMA, **to_primitive(self)}

    @classmethod
    def from_dict(cls, value):
        return cls(**_decode(value, cls, REFERENCE_SCHEMA))


def scalar_wire(value):
    return value.to_dict() if type(value) in (MemoryRef, DerivedResultRef) else value


def scalar_decode(value):
    if type(value) is dict:
        return (DerivedResultRef.from_dict(value) if value.get('schema_version') == REFERENCE_SCHEMA
                else MemoryRef.from_dict(value))
    _rational(value)
    return value


def parameters_check(values):
    require(type(values) is tuple and len(values) == 5 and all(type(r) is tuple and len(r) == 2 for r in values)
            and tuple(r[0] for r in values) == ('a', 'b', 'c', 'd', 'e'), 'exact sorted a..e parameters required')
    for _, value in values:
        if type(value) in (MemoryRef, DerivedResultRef):
            type(value).from_dict(value.to_dict())
        else:
            _rational(value)


def parameters_decode(values):
    require(type(values) is list and len(values) == 5 and all(type(r) is list and len(r) == 2 for r in values),
            'parameter wire pairs invalid')
    return tuple((r[0], scalar_decode(r[1])) for r in values)


@dataclass(frozen=True, slots=True)
class DerivedDefinition:
    scope: str
    key: str
    revision: int
    supersedes: str | None
    variable: str
    parameters: tuple

    def __post_init__(self):
        require(type(self) is DerivedDefinition, 'exact derived definition required')
        DerivedResultRef(self.scope, self.key)
        require(type(self.revision) is int and 1 <= self.revision <= MAX_MEMORIES, 'definition revision invalid')
        _sha(self.supersedes, 'definition predecessor', optional=True)
        require((self.revision == 1) == (self.supersedes is None), 'definition genesis/revision mismatch')
        _identifier(self.variable, 'derived variable')
        parameters_check(self.parameters)
        compound_problem({k: v if type(v) is str else '0' for k, v in self.parameters}, variable=self.variable)

    @property
    def definition_digest(self):
        return digest(self.to_dict())

    @property
    def ref(self):
        return DerivedResultRef(self.scope, self.key)

    def to_dict(self):
        return {'schema_version': DEFINITION_SCHEMA, 'scope': self.scope, 'key': self.key,
                'revision': self.revision, 'supersedes': self.supersedes, 'variable': self.variable,
                'parameters': [[k, scalar_wire(v)] for k, v in self.parameters]}

    @classmethod
    def from_dict(cls, value):
        body = _decode(value, cls, DEFINITION_SCHEMA)
        body['parameters'] = parameters_decode(body['parameters'])
        result = cls(**body)
        require(canonical_json(result.to_dict()) == canonical_json(value), 'definition wire is lossy')
        return result


@dataclass(frozen=True, slots=True)
class DerivedProblem:
    reasoning: ProblemPacket
    variable: str
    parameters: tuple
    budget: NativeBudget = DEFAULT_BUDGET
    updates: tuple = ()
    definitions: tuple = ()
    store_result: DerivedResultRef | None = None
    construction_limit: int = 420

    def __post_init__(self):
        require(type(self) is DerivedProblem, 'exact derived problem required')
        require(type(self.reasoning) is ProblemPacket and type(self.budget) is NativeBudget,
                'typed derived reasoning packet and budget required')
        require(type(self.updates) is tuple and len(self.updates) <= 256
                and all(type(s) is SourceStatement for s in self.updates), 'immutable typed source update tuple required')
        parameters_check(self.parameters)
        require(type(self.definitions) is tuple and len(self.definitions) <= 16
                and all(type(d) is DerivedDefinition for d in self.definitions), 'definition update bound/type invalid')
        require(len({d.ref for d in self.definitions}) == len(self.definitions), 'duplicate definition update key')
        require(self.store_result is None or type(self.store_result) is DerivedResultRef, 'typed store result required')
        self.compound_packet({}, placeholder=True)
        _bounded_json(self.to_dict(), 1024*1024, 'derived problem')

    @property
    def query_variable(self):
        return self.variable

    @property
    def input_hash(self):
        return digest(self.to_dict())

    @property
    def derived_references(self):
        return tuple(sorted({v for _, v in self.parameters if type(v) is DerivedResultRef}, key=lambda r: r.ref_key))

    def compound_packet(self, values, *, placeholder=False):
        parameters = []
        for k, v in self.parameters:
            if type(v) is DerivedResultRef:
                require(placeholder or v.ref_key in values, 'derived reference unresolved')
                v = values.get(v.ref_key, '0')
            parameters.append((k, v))
        return CompoundProblem(self.reasoning, self.variable, tuple(parameters), self.budget,
                               self.updates, self.construction_limit)

    def to_dict(self):
        return {'schema_version': PROBLEM_SCHEMA, 'reasoning': self.reasoning.to_dict(),
                'variable': self.variable, 'parameters': [[k, scalar_wire(v)] for k, v in self.parameters],
                'budget': self.budget.to_dict(), 'updates': [s.to_dict() for s in self.updates],
                'definitions': [d.to_dict() for d in self.definitions],
                'store_result': self.store_result.to_dict() if self.store_result else None,
                'construction_limit': self.construction_limit}

    @classmethod
    def from_dict(cls, value):
        body = _decode(value, cls, PROBLEM_SCHEMA)
        body['reasoning'] = ProblemPacket.from_dict(body['reasoning'])
        body['parameters'] = parameters_decode(body['parameters'])
        body['budget'] = NativeBudget.from_dict(body['budget'])
        require(type(body['updates']) is list and len(body['updates']) <= 256, 'source update list bound invalid')
        require(type(body['definitions']) is list and len(body['definitions']) <= 16, 'definition list bound invalid')
        body['updates'] = tuple(SourceStatement.from_dict(s) for s in body['updates'])
        body['definitions'] = tuple(DerivedDefinition.from_dict(d) for d in body['definitions'])
        body['store_result'] = DerivedResultRef.from_dict(body['store_result']) if body['store_result'] is not None else None
        result = cls(**body)
        require(canonical_json(result.to_dict()) == canonical_json(value), 'derived problem wire is lossy')
        return result


def create_problem(parameters, *, variable='x', problem_id='derived-problem', goal_id='derived-goal',
                   budget=DEFAULT_BUDGET, updates=(), definitions=(), store_result=None,
                   max_ticks=192, rpm_depth_limit=8, construction_limit=420):
    require(type(parameters) is dict and set(parameters) == set('abcde'), 'exact a..e map required')
    base = compound_problem({k: v if type(v) in (str, MemoryRef) else '0' for k, v in parameters.items()},
        variable=variable, problem_id=problem_id, goal_id=goal_id, budget=budget, updates=updates,
        max_ticks=max_ticks, rpm_depth_limit=rpm_depth_limit, construction_limit=construction_limit)
    return DerivedProblem(base.reasoning, variable, tuple(sorted(parameters.items())), budget,
                          updates, definitions, store_result, construction_limit)


@dataclass(frozen=True, slots=True)
class DerivedFrame:
    frame_id: str
    goal_id: str
    parent_goal_id: str
    parent_problem_digest: str
    parent_branch_digest: str
    reference: DerivedResultRef
    definition_digest: str
    return_address: str
    resume_stage: str
    depth: int
    entry_instruction_budget: int
    entry_checker_budget: int

    def __post_init__(self):
        require(type(self) is DerivedFrame and type(self.reference) is DerivedResultRef, 'typed derived frame required')
        for name in ('frame_id', 'goal_id', 'parent_goal_id'):
            _identifier(getattr(self, name), name)
        for name in ('parent_problem_digest', 'parent_branch_digest', 'definition_digest'):
            _sha(getattr(self, name), name)
        require(self.return_address == 'derived:'+digest(self.reference.to_dict()) and self.resume_stage == 'RESOLVE_COMPOUND_INPUTS',
                'derived continuation address invalid')
        require(type(self.depth) is int and self.depth == 1, 'derived acquisition depth is exactly one')
        NativeBudget(self.entry_instruction_budget, self.entry_checker_budget)

    def to_dict(self):
        return {'schema_version': FRAME_SCHEMA, **to_primitive(self), 'reference': self.reference.to_dict()}

    @classmethod
    def from_dict(cls, value):
        body = _decode(value, cls, FRAME_SCHEMA)
        body['reference'] = DerivedResultRef.from_dict(body['reference'])
        return cls(**body)


@dataclass(frozen=True, slots=True)
class DerivedRecord:
    kind: str
    body_json: str
    record_digest: str

    def __post_init__(self):
        require(type(self) is DerivedRecord and self.kind in {'DEFINITION', 'INSPECTION', 'CANDIDATE', 'CHECK', 'MEMORY',
                'RETURN', 'FAILURE', 'WORK_RESERVATION', 'USE'}, 'derived record kind invalid')
        require(type(self.body_json) is str and len(self.body_json) <= 1024*1024, 'derived record bytes exceeded')
        body = json.loads(self.body_json)
        require(type(body) is dict and _bounded_json(body, 1024*1024, 'derived record') == self.body_json,
                'derived record JSON invalid')
        require(self.record_digest == digest({'schema_version': RECORD_SCHEMA, 'kind': self.kind, 'body': body}), 'derived record seal invalid')

    @classmethod
    def create(cls, kind, body):
        raw = _bounded_json(body, 1024*1024, 'derived record')
        return cls(kind, raw, digest({'schema_version': RECORD_SCHEMA, 'kind': kind, 'body': body}))

    def body_dict(self):
        return json.loads(self.body_json)

    def to_dict(self):
        return {'schema_version': RECORD_SCHEMA, **to_primitive(self)}

    @classmethod
    def from_dict(cls, value):
        return cls(**_decode(value, cls, RECORD_SCHEMA))


@dataclass(frozen=True, slots=True, kw_only=True)
class DerivedState(CompoundState):
    derived_definitions: tuple = ()
    derived_records: tuple = ()
    derived_bindings: tuple = ()
    definition_update_index: int = 0
    derived_failure: str | None = None
    derived_stored: bool = False

    def __post_init__(self):
        require(type(self) is DerivedState and self.runtime_version == VERSION and self.constitution_revision == CONSTITUTION,
                'derived state version/type invalid')
        require(type(self.rpm_stack) is tuple, 'derived RPM stack must be an immutable tuple')
        inherited = {f.name: getattr(self, f.name) for f in fields(CompoundState)}
        inherited.update(runtime_version=OLD_VERSION, constitution_revision=OLD_CONSTITUTION,
                         rpm_stack=tuple(r for r in self.rpm_stack if type(r) is CompoundFrame))
        CompoundState(**inherited)
        require(type(self.derived_definitions) is tuple and len(self.derived_definitions) <= MAX_MEMORIES
                and all(type(d) is DerivedDefinition for d in self.derived_definitions), 'definition history invalid')
        require(type(self.derived_records) is tuple and len(self.derived_records) <= MAX_RECORDS
                and all(type(d) is DerivedRecord for d in self.derived_records), 'derived record history invalid')
        require(len({r.record_digest for r in self.derived_records}) == len(self.derived_records), 'duplicate derived record')
        require(type(self.derived_bindings) is tuple and len(self.derived_bindings) <= 5, 'derived binding bound invalid')
        for row in self.derived_bindings:
            require(type(row) is tuple and len(row) == 3, 'derived binding invalid')
            DerivedResultRef(row[0], row[1]); _sha(row[2], 'derived binding memory')
        require(len({r[:2] for r in self.derived_bindings}) == len(self.derived_bindings), 'duplicate derived binding')
        require(type(self.definition_update_index) is int and 0 <= self.definition_update_index <= 16, 'definition update index invalid')
        require(type(self.derived_stored) is bool, 'derived stored flag invalid')
        require(self.derived_failure is None or type(self.derived_failure) is str, 'derived failure invalid')
        require(all(type(r) in (CompoundFrame, DerivedFrame) for r in self.rpm_stack), 'unknown RPM frame')
        if any(type(r) is DerivedFrame for r in self.rpm_stack):
            require(len(self.rpm_stack) == 1 and self.compound_call is None, 'derived and compound acquisition cannot overlap')
        _bounded_json(self.to_dict(), 8*1024*1024, 'derived state')

    def to_dict(self):
        body = CompoundState.to_dict(self)
        body.update(schema_version=STATE_SCHEMA, derived_definitions=[d.to_dict() for d in self.derived_definitions],
                    derived_records=[r.to_dict() for r in self.derived_records],
                    derived_bindings=[list(r) for r in self.derived_bindings])
        return body

    @classmethod
    def from_dict(cls, value):
        body = _decode(value, cls, STATE_SCHEMA)
        _bounded_json(value, 8*1024*1024, 'derived state')
        inherited = {f.name: body[f.name] for f in fields(CompoundState)}
        inherited.update(schema_version=OLD_STATE_SCHEMA, runtime_version=OLD_VERSION, constitution_revision=OLD_CONSTITUTION,
                         rpm_stack=[r for r in body['rpm_stack'] if r.get('schema_version') != FRAME_SCHEMA])
        inherited['state_hash'] = digest({k:v for k,v in inherited.items() if k not in {'state_hash', 'trace_head'}})
        old = CompoundState.from_dict(inherited)
        args = {f.name:getattr(old, f.name) for f in fields(CompoundState)}
        args.update(runtime_version=body['runtime_version'], constitution_revision=body['constitution_revision'],
                    state_hash=body['state_hash'], rpm_stack=tuple(DerivedFrame.from_dict(r) if r.get('schema_version') == FRAME_SCHEMA
                        else CompoundFrame.from_dict(r) for r in body['rpm_stack']))
        args.update(derived_definitions=tuple(DerivedDefinition.from_dict(d) for d in body['derived_definitions']),
                    derived_records=tuple(DerivedRecord.from_dict(r) for r in body['derived_records']),
                    derived_bindings=tuple(tuple(r) for r in body['derived_bindings']),
                    definition_update_index=body['definition_update_index'], derived_failure=body['derived_failure'],
                    derived_stored=body['derived_stored'])
        result = cls(**args)
        require(result.state_hash == result.computed_hash() and canonical_json(result.to_dict()) == canonical_json(value),
                'derived state hash/roundtrip invalid')
        return result
