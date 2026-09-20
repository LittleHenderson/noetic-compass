"""Isolated exact-rational candidate substrate; no kernel installation authority.

The closed six-instruction grammar admits twelve input-dependent candidates.
SUCCESS means execution completed, not that a candidate solved a mathematical
problem. An independent checker and a future versioned kernel transition are
still required. This module has no registry, promotion, I/O, or model imports.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import gcd
import re

from .canonical import digest

ARTIFACT_SCHEMA = "cncm.procedure-substrate-artifact/0.1"
EXECUTION_SCHEMA = "cncm.procedure-substrate-execution/0.1"
EXECUTOR_REVISION = "cncm.six-instruction-rational-executor/0.1"
CAPABILITY_CONTRACT = "cncm.rational-two-op-candidate/0.1"
CLAIM_BOUNDARY = "SUBSTRATE_CANDIDATE_ONLY"
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_RATIONAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?\Z")


class ProcedureContractError(ValueError):
    """Malformed, unsupported, or unbound candidate data."""


class _ArithmeticLimit(ValueError):
    pass


def _require(condition, reason):
    if not condition:
        raise ProcedureContractError(reason)


def _keys(value, required, label):
    _require(type(value) is dict and set(value) == set(required), label + "_FIELDS_INVALID")


def _sha(value, label):
    _require(type(value) is str and _SHA256.fullmatch(value) is not None,
             label + "_DIGEST_INVALID")


@dataclass(frozen=True, slots=True)
class ProcedureLimits:
    input_bits: int = 128
    intermediate_bits: int = 512

    def __post_init__(self):
        _require(type(self.input_bits) is int and 2 <= self.input_bits <= 128,
                 "INPUT_BIT_LIMIT_INVALID")
        _require(type(self.intermediate_bits) is int
                 and self.input_bits <= self.intermediate_bits <= 512,
                 "INTERMEDIATE_BIT_LIMIT_INVALID")

    def to_dict(self):
        return {"input_bits": self.input_bits, "intermediate_bits": self.intermediate_bits}

    @classmethod
    def from_dict(cls, value):
        _keys(value, {"input_bits", "intermediate_bits"}, "LIMITS")
        return cls(**value)


@dataclass(frozen=True, slots=True)
class ProposalProvenance:
    """Self-described source identity; this does not authenticate an issuer."""
    source_id: str = "local-finite-grammar"
    source_revision: str = "0.1"

    def __post_init__(self):
        for value in (self.source_id, self.source_revision):
            _require(type(value) is str and _IDENTIFIER.fullmatch(value) is not None,
                     "PROPOSAL_PROVENANCE_INVALID")

    def to_dict(self):
        return {"source_id": self.source_id, "source_revision": self.source_revision}

    @classmethod
    def from_dict(cls, value):
        _keys(value, {"source_id", "source_revision"}, "PROVENANCE")
        return cls(**value)


@dataclass(frozen=True, slots=True)
class Instruction:
    operation: str
    target: str
    arguments: tuple[str, ...]

    def __post_init__(self):
        _require(type(self.operation) is str and self.operation in {
            "LOAD_INPUT", "ADD_EXACT", "SUBTRACT_EXACT", "DIVIDE_EXACT", "EMIT_REGISTER"
        }, "INSTRUCTION_OPERATION_INVALID")
        _require(type(self.target) is str and self.target in {"r0", "r1", "r2", "r3", "r4", "x"},
                 "INSTRUCTION_TARGET_INVALID")
        _require(type(self.arguments) is tuple and 1 <= len(self.arguments) <= 2
                 and all(type(item) is str and item in {"a", "b", "c", "r0", "r1", "r2", "r3", "r4"}
                         for item in self.arguments), "INSTRUCTION_ARGUMENTS_INVALID")

    def to_dict(self):
        return {"operation": self.operation, "target": self.target,
                "arguments": list(self.arguments)}

    @classmethod
    def from_dict(cls, value):
        _keys(value, {"operation", "target", "arguments"}, "INSTRUCTION")
        _require(type(value["arguments"]) is list and 1 <= len(value["arguments"]) <= 2,
                 "INSTRUCTION_ARGUMENTS_INVALID")
        return cls(value["operation"], value["target"], tuple(value["arguments"]))


def _validate_program(program):
    _require(type(program) is tuple and len(program) == 6
             and all(type(item) is Instruction for item in program), "PROGRAM_SHAPE_INVALID")
    for index in range(3):
        row = program[index]
        _require(row.operation == "LOAD_INPUT" and row.target == f"r{index}"
                 and len(row.arguments) == 1 and row.arguments[0] in ("a", "b", "c"),
                 "PROGRAM_LOAD_SEQUENCE_INVALID")
    _require({row.arguments[0] for row in program[:3]} == {"a", "b", "c"},
             "PROGRAM_INPUT_COVERAGE_INVALID")
    _require(program[3].operation in ("ADD_EXACT", "SUBTRACT_EXACT")
             and program[3].target == "r3" and program[3].arguments == ("r0", "r1"),
             "PROGRAM_COMBINE_INVALID")
    _require(program[4] == Instruction("DIVIDE_EXACT", "r4", ("r3", "r2")),
             "PROGRAM_DIVISION_INVALID")
    _require(program[5] == Instruction("EMIT_REGISTER", "x", ("r4",)),
             "PROGRAM_OUTPUT_INVALID")


@dataclass(frozen=True, slots=True)
class ProcedureArtifact:
    program: tuple[Instruction, ...]
    limits: ProcedureLimits = ProcedureLimits()
    provenance: ProposalProvenance = ProposalProvenance()
    revision: int = 1

    def __post_init__(self):
        _validate_program(self.program)
        _require(type(self.limits) is ProcedureLimits, "ARTIFACT_LIMITS_INVALID")
        _require(type(self.provenance) is ProposalProvenance, "ARTIFACT_PROVENANCE_INVALID")
        _require(type(self.revision) is int and 1 <= self.revision < 2**31,
                 "ARTIFACT_REVISION_INVALID")

    def _body(self):
        return {"schema_version": ARTIFACT_SCHEMA, "executor_revision": EXECUTOR_REVISION,
                "capability_contract": CAPABILITY_CONTRACT, "claim_boundary": CLAIM_BOUNDARY,
                "input_names": ["a", "b", "c"], "output_names": ["x"],
                "revision": self.revision, "limits": self.limits.to_dict(),
                "provenance": self.provenance.to_dict(),
                "program": [row.to_dict() for row in self.program]}

    @property
    def artifact_sha256(self):
        return digest(self._body())

    def to_dict(self):
        return {**self._body(), "artifact_sha256": self.artifact_sha256}

    @classmethod
    def from_dict(cls, value):
        _keys(value, {"schema_version", "executor_revision", "capability_contract",
                      "claim_boundary", "input_names", "output_names", "revision", "limits",
                      "provenance", "program", "artifact_sha256"}, "ARTIFACT")
        _require(value["schema_version"] == ARTIFACT_SCHEMA
                 and value["executor_revision"] == EXECUTOR_REVISION
                 and value["capability_contract"] == CAPABILITY_CONTRACT
                 and value["claim_boundary"] == CLAIM_BOUNDARY
                 and value["input_names"] == ["a", "b", "c"] and value["output_names"] == ["x"],
                 "ARTIFACT_CONTRACT_INVALID")
        _require(type(value["program"]) is list and len(value["program"]) == 6,
                 "PROGRAM_SHAPE_INVALID")
        artifact = cls(tuple(Instruction.from_dict(row) for row in value["program"]),
                       ProcedureLimits.from_dict(value["limits"]),
                       ProposalProvenance.from_dict(value["provenance"]), value["revision"])
        _sha(value["artifact_sha256"], "ARTIFACT")
        _require(value["artifact_sha256"] == artifact.artifact_sha256, "ARTIFACT_DIGEST_MISMATCH")
        return artifact


def make_candidate(load_order=("c", "b", "a"), combine="SUBTRACT_EXACT", *,
                   limits=ProcedureLimits(), provenance=ProposalProvenance(), revision=1):
    _require(type(load_order) is tuple and len(load_order) == 3
             and all(type(item) is str for item in load_order), "LOAD_ORDER_INVALID")
    program = tuple(Instruction("LOAD_INPUT", f"r{index}", (name,))
                    for index, name in enumerate(load_order)) + (
        Instruction(combine, "r3", ("r0", "r1")),
        Instruction("DIVIDE_EXACT", "r4", ("r3", "r2")),
        Instruction("EMIT_REGISTER", "x", ("r4",)),
    )
    return ProcedureArtifact(program, limits, provenance, revision)


def _rational_text(value):
    numerator, denominator = value
    return str(numerator) if denominator == 1 else f"{numerator}/{denominator}"


def _parse_rational(text, bits):
    # Bound text before regex, decimal conversion, or gcd. No arbitrary-size
    # integer can enter through the public wire format.
    digits = len(str((1 << bits) - 1))
    _require(type(text) is str and 1 <= len(text) <= 2 * digits + 2,
             "RATIONAL_TEXT_BOUND_EXCEEDED")
    _require(_RATIONAL.fullmatch(text) is not None, "RATIONAL_SYNTAX_INVALID")
    numerator_text, separator, denominator_text = text.partition("/")
    _require(len(numerator_text.lstrip("-")) <= digits
             and (not separator or len(denominator_text) <= digits), "RATIONAL_DIGIT_BOUND_EXCEEDED")
    numerator = int(numerator_text)
    denominator = int(denominator_text) if separator else 1
    _require(abs(numerator).bit_length() <= bits and denominator.bit_length() <= bits,
             "RATIONAL_BIT_BOUND_EXCEEDED")
    divisor = gcd(abs(numerator), denominator)
    normalized = (numerator // divisor, denominator // divisor)
    _require(_rational_text(normalized) == text, "RATIONAL_NOT_CANONICAL")
    return normalized


def _product_bound(left, right):
    return 0 if left == 0 or right == 0 else abs(left).bit_length() + abs(right).bit_length()


def _multiply(left, right):
    """Allocation seam called only after the complete operation's preflight."""
    return left * right


def _arithmetic(operation, left, right, bits):
    ln, ld = left
    rn, rd = right
    if operation in ("ADD_EXACT", "SUBTRACT_EXACT"):
        numerator_bound = max(_product_bound(ln, rd), _product_bound(rn, ld)) + 1
        denominator_bound = _product_bound(ld, rd)
    else:
        if rn == 0:
            raise ZeroDivisionError("candidate denominator is zero")
        numerator_bound = _product_bound(ln, rd)
        denominator_bound = _product_bound(ld, rn)
    # Conservative bounds can reject a reducible/canceling expression. That
    # is intentional: reduction must not be used to justify a huge allocation.
    if max(numerator_bound, denominator_bound) > bits:
        raise _ArithmeticLimit("pre-arithmetic intermediate bound exceeded")
    if operation == "ADD_EXACT":
        numerator = _multiply(ln, rd) + _multiply(rn, ld)
        denominator = _multiply(ld, rd)
    elif operation == "SUBTRACT_EXACT":
        numerator = _multiply(ln, rd) - _multiply(rn, ld)
        denominator = _multiply(ld, rd)
    else:
        numerator = _multiply(ln, rd)
        denominator = _multiply(ld, rn)
    if denominator < 0:
        numerator, denominator = -numerator, -denominator
    divisor = gcd(abs(numerator), denominator)
    return numerator // divisor, denominator // divisor


@dataclass(frozen=True, slots=True)
class ProcedureExecution:
    artifact_sha256: str
    inputs_sha256: str
    instruction_budget: int
    status: str
    output: str | None
    instructions_executed: int

    def __post_init__(self):
        _sha(self.artifact_sha256, "EXECUTION_ARTIFACT")
        _sha(self.inputs_sha256, "EXECUTION_INPUTS")
        _require(type(self.instruction_budget) is int and 0 <= self.instruction_budget <= 6,
                 "EXECUTION_BUDGET_INVALID")
        _require(type(self.instructions_executed) is int
                 and 0 <= self.instructions_executed <= self.instruction_budget,
                 "EXECUTION_COST_INVALID")
        _require(self.status in ("SUCCESS", "DIVISION_BY_ZERO", "ARITHMETIC_LIMIT", "BUDGET_EXHAUSTED"),
                 "EXECUTION_STATUS_INVALID")
        if self.status == "SUCCESS":
            _require(self.instructions_executed == 6 and self.output is not None,
                     "EXECUTION_SUCCESS_SHAPE_INVALID")
            _parse_rational(self.output, 512)
        else:
            expected = {"DIVISION_BY_ZERO": (5,), "ARITHMETIC_LIMIT": (4, 5),
                        "BUDGET_EXHAUSTED": (0,)}[self.status]
            _require(self.output is None and self.instructions_executed in expected,
                     "EXECUTION_FAILURE_SHAPE_INVALID")
            _require((self.instruction_budget < 6) == (self.status == "BUDGET_EXHAUSTED"),
                     "EXECUTION_FAILURE_BUDGET_INVALID")

    def _body(self):
        return {"schema_version": EXECUTION_SCHEMA, "executor_revision": EXECUTOR_REVISION,
                "claim_boundary": CLAIM_BOUNDARY, "artifact_sha256": self.artifact_sha256,
                "inputs_sha256": self.inputs_sha256, "instruction_budget": self.instruction_budget,
                "status": self.status, "outputs": {} if self.output is None else {"x": self.output},
                "instructions_executed": self.instructions_executed}

    def to_dict(self):
        value = self._body()
        return {**value, "report_sha256": digest(value)}

    @classmethod
    def from_dict(cls, value):
        _keys(value, {"schema_version", "executor_revision", "claim_boundary", "artifact_sha256",
                      "inputs_sha256", "instruction_budget", "status", "outputs",
                      "instructions_executed", "report_sha256"}, "EXECUTION")
        _require(value["schema_version"] == EXECUTION_SCHEMA
                 and value["executor_revision"] == EXECUTOR_REVISION
                 and value["claim_boundary"] == CLAIM_BOUNDARY, "EXECUTION_CONTRACT_INVALID")
        outputs = value["outputs"]
        _require(type(outputs) is dict and (set(outputs) == {"x"} if value["status"] == "SUCCESS"
                                            else not outputs), "EXECUTION_OUTPUTS_INVALID")
        report = cls(value["artifact_sha256"], value["inputs_sha256"], value["instruction_budget"],
                     value["status"], outputs.get("x"), value["instructions_executed"])
        _sha(value["report_sha256"], "EXECUTION_REPORT")
        _require(report.to_dict()["report_sha256"] == value["report_sha256"], "EXECUTION_DIGEST_MISMATCH")
        return report


def execute_procedure(artifact, inputs, *, instruction_budget=6):
    _require(type(artifact) is ProcedureArtifact, "EXECUTION_ARTIFACT_INVALID")
    # Revalidate complete immutable content, including its closed program.
    artifact = ProcedureArtifact.from_dict(artifact.to_dict())
    _keys(inputs, {"a", "b", "c"}, "INPUTS")
    values = {name: _parse_rational(inputs[name], artifact.limits.input_bits) for name in ("a", "b", "c")}
    _require(type(instruction_budget) is int and 0 <= instruction_budget <= 6,
             "EXECUTION_BUDGET_INVALID")
    input_digest = digest({"input_contract": CAPABILITY_CONTRACT, "inputs": dict(inputs)})
    def result(status, output, count):
        return ProcedureExecution(artifact.artifact_sha256, input_digest, instruction_budget,
                                  status, output, count)
    if instruction_budget < 6:
        return result("BUDGET_EXHAUSTED", None, 0)
    registers = {}
    for count, row in enumerate(artifact.program, 1):
        if row.operation == "LOAD_INPUT":
            registers[row.target] = values[row.arguments[0]]
        elif row.operation == "EMIT_REGISTER":
            return result("SUCCESS", _rational_text(registers[row.arguments[0]]), count)
        else:
            try:
                registers[row.target] = _arithmetic(row.operation, registers[row.arguments[0]],
                                                     registers[row.arguments[1]],
                                                     artifact.limits.intermediate_bits)
            except _ArithmeticLimit:
                return result("ARITHMETIC_LIMIT", None, count)
            except ZeroDivisionError:
                return result("DIVISION_BY_ZERO", None, count)
    raise ProcedureContractError("PROGRAM_OUTPUT_MISSING")


def replay_execution(artifact, inputs, report):
    """Re-execute under the bound budget and compare every report field."""
    try:
        parsed = ProcedureExecution.from_dict(report.to_dict() if type(report) is ProcedureExecution else report)
        expected = execute_procedure(artifact, inputs, instruction_budget=parsed.instruction_budget)
        return expected.to_dict() == parsed.to_dict()
    except (ProcedureContractError, TypeError, ValueError, KeyError, OverflowError):
        return False
