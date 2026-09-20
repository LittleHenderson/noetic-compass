"""Frozen CAS-Math v0.1 objects with exact rational arithmetic.

The cognitive machine may propose mathematical work.  These objects do not
grant proposals mathematical authority; acceptance is produced only by the
protected checker in :mod:`cncm.math_kernel`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import gcd
import re
from typing import Any, Iterable, Mapping, TypeAlias

from .canonical import content_id, digest
from .model import ContractError, Provenance


MATH_PROBLEM_SCHEMA_VERSION = "cncm.math-problem/0.1"
MATH_RESULT_SCHEMA_VERSION = "cncm.math-result/0.1"
MATH_THEORY_ID = "cncm.q-linear/0.1"
MATH_CHECKER_VERSION = "cncm.math-checker/0.1"
MATH_BRANCH_ID = "math_root"
MATH_MAX_PREMISES = 64
MATH_MAX_DERIVATION_DEPTH = 128
MATH_MAX_RECEIPT_RECHECKS = 4096
_SYMBOL = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MATH_RECEIPT_ID = re.compile(r"^math-receipt-[0-9a-f]{16}$")


class MathContractError(ContractError):
    """A CAS-Math wire or semantic contract was violated."""


class MathGuardError(MathContractError):
    """An exact operation requires a guard that was not discharged."""


class MathCapabilityError(MathContractError):
    """The requested operation is outside the frozen CAS-Math MVP."""


class MathBudgetError(MathContractError):
    """A frozen parser, proof, or search budget was exhausted."""


def _strict_keys(
    data: Mapping[str, Any],
    required: set[str],
    optional: set[str],
    label: str,
) -> None:
    if not isinstance(data, Mapping):
        raise MathContractError(f"{label} must be an object")
    missing = required - set(data)
    extra = set(data) - required - optional
    if missing:
        raise MathContractError(f"{label} missing keys: {sorted(missing)}")
    if extra:
        raise MathContractError(f"{label} unknown keys: {sorted(extra)}")


def _strict_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise MathContractError(f"{label} must be an integer")
    return value


def _symbol(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SYMBOL.fullmatch(value):
        raise MathContractError(f"{label} must be an ASCII identifier")
    return value


def _nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise MathContractError(f"{label} must be a nonempty string")
    return value


@dataclass(frozen=True, slots=True)
class ExactRational:
    """A canonical exact rational; floats never enter CAS-Math state."""

    numerator: int
    denominator: int = 1

    def __post_init__(self) -> None:
        numerator = _strict_int(self.numerator, "ExactRational.numerator")
        denominator = _strict_int(self.denominator, "ExactRational.denominator")
        if denominator == 0:
            raise MathGuardError("rational denominator must be nonzero")
        if denominator < 0:
            numerator = -numerator
            denominator = -denominator
        divisor = gcd(abs(numerator), denominator)
        if numerator == 0:
            denominator = 1
        else:
            numerator //= divisor
            denominator //= divisor
        object.__setattr__(self, "numerator", numerator)
        object.__setattr__(self, "denominator", denominator)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExactRational":
        _strict_keys(data, {"numerator", "denominator"}, set(), "ExactRational")
        return cls(
            _strict_int(data["numerator"], "ExactRational.numerator"),
            _strict_int(data["denominator"], "ExactRational.denominator"),
        )

    @classmethod
    def from_int(cls, value: int) -> "ExactRational":
        return cls(_strict_int(value, "integer"), 1)

    @property
    def is_zero(self) -> bool:
        return self.numerator == 0

    @property
    def is_integer(self) -> bool:
        return self.denominator == 1

    @property
    def sign(self) -> int:
        return (self.numerator > 0) - (self.numerator < 0)

    def __neg__(self) -> "ExactRational":
        return ExactRational(-self.numerator, self.denominator)

    def __add__(self, other: "ExactRational") -> "ExactRational":
        if not isinstance(other, ExactRational):
            return NotImplemented
        return ExactRational(
            self.numerator * other.denominator + other.numerator * self.denominator,
            self.denominator * other.denominator,
        )

    def __sub__(self, other: "ExactRational") -> "ExactRational":
        if not isinstance(other, ExactRational):
            return NotImplemented
        return self + (-other)

    def __mul__(self, other: "ExactRational") -> "ExactRational":
        if not isinstance(other, ExactRational):
            return NotImplemented
        return ExactRational(
            self.numerator * other.numerator,
            self.denominator * other.denominator,
        )

    def __truediv__(self, other: "ExactRational") -> "ExactRational":
        if not isinstance(other, ExactRational):
            return NotImplemented
        if other.is_zero:
            raise MathGuardError("division by zero is not admissible")
        return ExactRational(
            self.numerator * other.denominator,
            self.denominator * other.numerator,
        )

    def __lt__(self, other: "ExactRational") -> bool:
        if not isinstance(other, ExactRational):
            return NotImplemented
        return self.numerator * other.denominator < other.numerator * self.denominator

    def __le__(self, other: "ExactRational") -> bool:
        return self == other or self < other

    def to_dict(self) -> dict[str, int]:
        return {"numerator": self.numerator, "denominator": self.denominator}

    def __str__(self) -> str:
        if self.denominator == 1:
            return str(self.numerator)
        return f"{self.numerator}/{self.denominator}"


@dataclass(frozen=True, slots=True)
class IntegerExpression:
    value: int

    def __post_init__(self) -> None:
        _strict_int(self.value, "IntegerExpression.value")

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "integer", "value": self.value}


@dataclass(frozen=True, slots=True)
class RationalExpression:
    value: ExactRational

    def __post_init__(self) -> None:
        if not isinstance(self.value, ExactRational):
            raise MathContractError("RationalExpression.value must be ExactRational")

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "rational", "value": self.value.to_dict()}


@dataclass(frozen=True, slots=True)
class VariableExpression:
    name: str

    def __post_init__(self) -> None:
        _symbol(self.name, "VariableExpression.name")

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "variable", "name": self.name}


@dataclass(frozen=True, slots=True)
class NegateExpression:
    operand: "MathExpression"

    def __post_init__(self) -> None:
        _require_expression(self.operand, "NegateExpression.operand")

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "negate", "operand": expression_to_dict(self.operand)}


@dataclass(frozen=True, slots=True)
class AddExpression:
    terms: tuple["MathExpression", ...]

    def __post_init__(self) -> None:
        if len(self.terms) < 2:
            raise MathContractError("AddExpression requires at least two terms")
        for term in self.terms:
            _require_expression(term, "AddExpression.term")

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "add", "terms": [expression_to_dict(item) for item in self.terms]}


@dataclass(frozen=True, slots=True)
class MultiplyExpression:
    factors: tuple["MathExpression", ...]

    def __post_init__(self) -> None:
        if len(self.factors) < 2:
            raise MathContractError("MultiplyExpression requires at least two factors")
        for factor in self.factors:
            _require_expression(factor, "MultiplyExpression.factor")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "multiply",
            "factors": [expression_to_dict(item) for item in self.factors],
        }


@dataclass(frozen=True, slots=True)
class DivideExpression:
    numerator: "MathExpression"
    denominator: "MathExpression"

    def __post_init__(self) -> None:
        _require_expression(self.numerator, "DivideExpression.numerator")
        _require_expression(self.denominator, "DivideExpression.denominator")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "divide",
            "numerator": expression_to_dict(self.numerator),
            "denominator": expression_to_dict(self.denominator),
        }


MathExpression: TypeAlias = (
    IntegerExpression
    | RationalExpression
    | VariableExpression
    | NegateExpression
    | AddExpression
    | MultiplyExpression
    | DivideExpression
)
_EXPRESSION_TYPES = (
    IntegerExpression,
    RationalExpression,
    VariableExpression,
    NegateExpression,
    AddExpression,
    MultiplyExpression,
    DivideExpression,
)


def _require_expression(value: Any, label: str) -> MathExpression:
    if not isinstance(value, _EXPRESSION_TYPES):
        raise MathContractError(f"{label} must be a CAS-Math expression")
    return value


def expression_to_dict(expression: MathExpression) -> dict[str, Any]:
    return _require_expression(expression, "expression").to_dict()


def expression_from_dict(
    data: Mapping[str, Any],
    *,
    max_depth: int = 64,
    max_nodes: int = 4096,
) -> MathExpression:
    counter = [0]

    def build(value: Mapping[str, Any], depth: int) -> MathExpression:
        if depth > max_depth:
            raise MathBudgetError("math expression depth budget exhausted")
        counter[0] += 1
        if counter[0] > max_nodes:
            raise MathBudgetError("math expression node budget exhausted")
        if not isinstance(value, Mapping):
            raise MathContractError("math expression node must be an object")
        kind = value.get("kind")
        if kind == "integer":
            _strict_keys(value, {"kind", "value"}, set(), "IntegerExpression")
            return IntegerExpression(_strict_int(value["value"], "IntegerExpression.value"))
        if kind == "rational":
            _strict_keys(value, {"kind", "value"}, set(), "RationalExpression")
            return RationalExpression(ExactRational.from_dict(value["value"]))
        if kind == "variable":
            _strict_keys(value, {"kind", "name"}, set(), "VariableExpression")
            return VariableExpression(_symbol(value["name"], "VariableExpression.name"))
        if kind == "negate":
            _strict_keys(value, {"kind", "operand"}, set(), "NegateExpression")
            return NegateExpression(build(value["operand"], depth + 1))
        if kind in {"add", "multiply"}:
            member = "terms" if kind == "add" else "factors"
            _strict_keys(value, {"kind", member}, set(), f"{kind} expression")
            raw = value[member]
            if not isinstance(raw, list) or len(raw) < 2:
                raise MathContractError(f"{kind} expression requires at least two {member}")
            items = tuple(build(item, depth + 1) for item in raw)
            return AddExpression(items) if kind == "add" else MultiplyExpression(items)
        if kind == "divide":
            _strict_keys(
                value,
                {"kind", "numerator", "denominator"},
                set(),
                "DivideExpression",
            )
            return DivideExpression(
                build(value["numerator"], depth + 1),
                build(value["denominator"], depth + 1),
            )
        raise MathContractError(f"unsupported math expression kind: {kind!r}")

    return build(data, 0)


def expression_variables(expression: MathExpression) -> tuple[str, ...]:
    found: set[str] = set()
    stack = [expression]
    while stack:
        current = stack.pop()
        if isinstance(current, VariableExpression):
            found.add(current.name)
        elif isinstance(current, NegateExpression):
            stack.append(current.operand)
        elif isinstance(current, AddExpression):
            stack.extend(current.terms)
        elif isinstance(current, MultiplyExpression):
            stack.extend(current.factors)
        elif isinstance(current, DivideExpression):
            stack.extend((current.numerator, current.denominator))
    return tuple(sorted(found))


def format_expression(expression: MathExpression) -> str:
    if isinstance(expression, IntegerExpression):
        return str(expression.value)
    if isinstance(expression, RationalExpression):
        return str(expression.value)
    if isinstance(expression, VariableExpression):
        return expression.name
    if isinstance(expression, NegateExpression):
        return f"-({format_expression(expression.operand)})"
    if isinstance(expression, AddExpression):
        return " + ".join(f"({format_expression(item)})" for item in expression.terms)
    if isinstance(expression, MultiplyExpression):
        return " * ".join(f"({format_expression(item)})" for item in expression.factors)
    if isinstance(expression, DivideExpression):
        return (
            f"({format_expression(expression.numerator)})"
            f"/({format_expression(expression.denominator)})"
        )
    raise MathContractError("unsupported expression")


class MathRelation(str, Enum):
    EQUAL = "EQUAL"
    LESS_THAN = "LESS_THAN"


@dataclass(frozen=True, slots=True)
class MathStatement:
    left: MathExpression
    relation: MathRelation
    right: MathExpression

    def __post_init__(self) -> None:
        _require_expression(self.left, "MathStatement.left")
        _require_expression(self.right, "MathStatement.right")
        if not isinstance(self.relation, MathRelation):
            raise MathContractError("MathStatement.relation must be typed")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MathStatement":
        _strict_keys(data, {"left", "relation", "right"}, set(), "MathStatement")
        try:
            relation = MathRelation(data["relation"])
        except (TypeError, ValueError) as exc:
            raise MathContractError("unsupported math relation") from exc
        return cls(
            expression_from_dict(data["left"]),
            relation,
            expression_from_dict(data["right"]),
        )

    @property
    def statement_id(self) -> str:
        return content_id("math-statement", self.to_dict())

    @property
    def variables(self) -> tuple[str, ...]:
        return tuple(sorted(set(expression_variables(self.left)) | set(expression_variables(self.right))))

    def to_dict(self) -> dict[str, Any]:
        return {
            "left": expression_to_dict(self.left),
            "relation": self.relation.value,
            "right": expression_to_dict(self.right),
        }

    def __str__(self) -> str:
        operator = "=" if self.relation is MathRelation.EQUAL else "<"
        return f"{format_expression(self.left)} {operator} {format_expression(self.right)}"


class MathClaimStatus(str, Enum):
    GIVEN = "GIVEN"
    ASSUMED = "ASSUMED"
    DERIVED = "DERIVED"
    CONJECTURED = "CONJECTURED"
    VERIFIED = "VERIFIED"
    DISPROVED = "DISPROVED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class MathClaim:
    claim_id: str
    statement: MathStatement
    status: MathClaimStatus
    theory_id: str
    assumption_claim_ids: tuple[str, ...]
    provenance: tuple[Provenance, ...]
    derivation_receipt_id: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.statement, MathStatement):
            raise MathContractError("MathClaim.statement must be typed")
        if not isinstance(self.status, MathClaimStatus):
            raise MathContractError("MathClaim.status must be typed")
        if self.theory_id != MATH_THEORY_ID:
            raise MathContractError(
                f"CAS-Math v0.1 only admits theory_id {MATH_THEORY_ID!r}"
            )
        if (
            not isinstance(self.assumption_claim_ids, tuple)
            or self.assumption_claim_ids != tuple(sorted(set(self.assumption_claim_ids)))
            or any(
                not isinstance(item, str)
                or re.fullmatch(r"math-claim-[0-9a-f]{16}", item) is None
                for item in self.assumption_claim_ids
            )
        ):
            raise MathContractError(
                "MathClaim.assumption_claim_ids must be sorted unique claim identifiers"
            )
        if (
            not isinstance(self.provenance, tuple)
            or any(not isinstance(item, Provenance) for item in self.provenance)
            or self.provenance
            != tuple(
                sorted(
                    self.provenance,
                    key=lambda item: (item.source_type, item.source_id, item.detail),
                )
            )
        ):
            raise MathContractError("MathClaim.provenance must be canonical typed provenance")
        checked_status = self.status in {
            MathClaimStatus.DERIVED,
            MathClaimStatus.VERIFIED,
        }
        if checked_status:
            if (
                not isinstance(self.derivation_receipt_id, str)
                or _MATH_RECEIPT_ID.fullmatch(self.derivation_receipt_id) is None
            ):
                raise MathContractError(
                    "derived and verified claims require a checked derivation receipt"
                )
            if not any(
                item.source_type == "math_receipt"
                and item.source_id == self.derivation_receipt_id
                for item in self.provenance
            ):
                raise MathContractError(
                    "checked claim provenance must cite its derivation receipt"
                )
        elif self.derivation_receipt_id is not None:
            raise MathContractError(
                "only derived or verified claims may bind a derivation receipt"
            )
        body = {
            "statement": self.statement.to_dict(),
            "status": self.status.value,
            "theory_id": self.theory_id,
            "assumption_claim_ids": list(self.assumption_claim_ids),
            "provenance": [item.to_dict() for item in self.provenance],
            "derivation_receipt_id": self.derivation_receipt_id,
        }
        if self.claim_id != content_id("math-claim", body):
            raise MathContractError("MathClaim.claim_id is not content-derived")

    @classmethod
    def _build(
        cls,
        *,
        statement: MathStatement,
        status: MathClaimStatus,
        theory_id: str,
        assumption_claim_ids: Iterable[str],
        provenance: Iterable[Provenance],
        derivation_receipt_id: str | None,
    ) -> "MathClaim":
        if not isinstance(statement, MathStatement):
            raise MathContractError("MathClaim.statement must be typed")
        if not isinstance(status, MathClaimStatus):
            raise MathContractError("MathClaim.status must be typed")
        if theory_id != MATH_THEORY_ID:
            raise MathContractError(
                f"CAS-Math v0.1 only admits theory_id {MATH_THEORY_ID!r}"
            )
        checked_status = status in {MathClaimStatus.DERIVED, MathClaimStatus.VERIFIED}
        if checked_status:
            if (
                not isinstance(derivation_receipt_id, str)
                or _MATH_RECEIPT_ID.fullmatch(derivation_receipt_id) is None
            ):
                raise MathContractError(
                    "derived and verified claims require a checked derivation receipt"
                )
        elif derivation_receipt_id is not None:
            raise MathContractError(
                "only derived or verified claims may bind a derivation receipt"
            )
        raw_assumptions = tuple(assumption_claim_ids)
        if any(
            not isinstance(item, str)
            or re.fullmatch(r"math-claim-[0-9a-f]{16}", item) is None
            for item in raw_assumptions
        ):
            raise MathContractError("assumption_claim_ids must contain claim identifiers")
        assumptions = tuple(sorted(set(raw_assumptions)))
        raw_sources = tuple(provenance)
        if any(not isinstance(item, Provenance) for item in raw_sources):
            raise MathContractError("MathClaim.provenance must contain typed provenance")
        sources = tuple(
            sorted(
                raw_sources,
                key=lambda item: (item.source_type, item.source_id, item.detail),
            )
        )
        if checked_status and not any(
            item.source_type == "math_receipt"
            and item.source_id == derivation_receipt_id
            for item in sources
        ):
            raise MathContractError(
                "checked claim provenance must cite its derivation receipt"
            )
        body = {
            "statement": statement.to_dict(),
            "status": status.value,
            "theory_id": theory_id,
            "assumption_claim_ids": list(assumptions),
            "provenance": [item.to_dict() for item in sources],
            "derivation_receipt_id": derivation_receipt_id,
        }
        return cls(
            content_id("math-claim", body),
            statement,
            status,
            theory_id,
            assumptions,
            sources,
            derivation_receipt_id,
        )

    @classmethod
    def create(
        cls,
        *,
        statement: MathStatement,
        status: MathClaimStatus,
        theory_id: str = MATH_THEORY_ID,
        assumption_claim_ids: Iterable[str] = (),
        provenance: Iterable[Provenance] = (),
    ) -> "MathClaim":
        if status in {MathClaimStatus.DERIVED, MathClaimStatus.VERIFIED}:
            raise MathContractError(
                "caller-created claims cannot assert DERIVED or VERIFIED status; "
                "use the protected checker claim-issuance path"
            )
        return cls._build(
            statement=statement,
            status=status,
            theory_id=theory_id,
            assumption_claim_ids=assumption_claim_ids,
            provenance=provenance,
            derivation_receipt_id=None,
        )

    @classmethod
    def _from_checked_receipt(
        cls,
        *,
        receipt: "MathStepReceipt",
        status: MathClaimStatus,
        assumption_claim_ids: Iterable[str] = (),
        provenance: Iterable[Provenance] = (),
    ) -> "MathClaim":
        """Construct after :mod:`math_kernel` has independently rechecked a receipt."""

        if status not in {MathClaimStatus.DERIVED, MathClaimStatus.VERIFIED}:
            raise MathContractError("checked claim issuance requires DERIVED or VERIFIED status")
        if not isinstance(receipt, MathStepReceipt) or not receipt.accepted:
            raise MathContractError("checked claim issuance requires an accepted receipt")
        if receipt.reconstructed_conclusion is None:
            raise MathContractError("accepted receipt is missing its reconstructed conclusion")
        receipt_provenance = tuple(provenance) + (
            Provenance("math_receipt", receipt.receipt_id, "protected_checker"),
        )
        return cls._build(
            statement=receipt.reconstructed_conclusion,
            status=status,
            theory_id=receipt.theory_id,
            assumption_claim_ids=assumption_claim_ids,
            provenance=receipt_provenance,
            derivation_receipt_id=receipt.receipt_id,
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MathClaim":
        _strict_keys(
            data,
            {
                "claim_id",
                "statement",
                "status",
                "theory_id",
                "assumption_claim_ids",
                "provenance",
                "derivation_receipt_id",
            },
            set(),
            "MathClaim",
        )
        try:
            status = MathClaimStatus(data["status"])
        except (TypeError, ValueError) as exc:
            raise MathContractError("unsupported math claim status") from exc
        if status in {MathClaimStatus.DERIVED, MathClaimStatus.VERIFIED}:
            raise MathContractError(
                "checked claims cannot be trusted by standalone deserialization; "
                "verify and semantically re-execute the containing proof bundle"
            )
        raw_assumptions = data["assumption_claim_ids"]
        raw_provenance = data["provenance"]
        if not isinstance(raw_assumptions, list) or any(not isinstance(item, str) for item in raw_assumptions):
            raise MathContractError("assumption_claim_ids must be a list of strings")
        if not isinstance(raw_provenance, list):
            raise MathContractError("provenance must be a list")
        rebuilt = cls._build(
            statement=MathStatement.from_dict(data["statement"]),
            status=status,
            theory_id=_nonempty(data["theory_id"], "MathClaim.theory_id"),
            assumption_claim_ids=raw_assumptions,
            provenance=(Provenance.from_dict(item) for item in raw_provenance),
            derivation_receipt_id=data["derivation_receipt_id"],
        )
        if data["claim_id"] != rebuilt.claim_id:
            raise MathContractError("MathClaim.claim_id is not content-derived")
        return rebuilt

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "statement": self.statement.to_dict(),
            "status": self.status.value,
            "theory_id": self.theory_id,
            "assumption_claim_ids": list(self.assumption_claim_ids),
            "provenance": [item.to_dict() for item in self.provenance],
            "derivation_receipt_id": self.derivation_receipt_id,
        }


class MathStepOperation(str, Enum):
    EVALUATE_EXACT = "EVALUATE_EXACT"
    SIMPLIFY_EXACT = "SIMPLIFY_EXACT"
    ADD_BOTH_SIDES = "ADD_BOTH_SIDES"
    SUBTRACT_BOTH_SIDES = "SUBTRACT_BOTH_SIDES"
    MULTIPLY_BOTH_SIDES = "MULTIPLY_BOTH_SIDES"
    DIVIDE_BOTH_SIDES = "DIVIDE_BOTH_SIDES"
    SUBSTITUTE = "SUBSTITUTE"
    TRANSITIVE_EQUAL = "TRANSITIVE_EQUAL"
    TRANSITIVE_LESS_THAN = "TRANSITIVE_LESS_THAN"
    VERIFY_LINEAR_SOLUTION = "VERIFY_LINEAR_SOLUTION"


@dataclass(frozen=True, slots=True)
class MathStepProposal:
    proposal_id: str
    operation: MathStepOperation
    premise_claim_ids: tuple[str, ...]
    proposed_conclusion: MathStatement
    parameter: MathExpression | None
    substitutions: tuple[tuple[str, MathExpression], ...]
    branch_id: str
    theory_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.operation, MathStepOperation):
            raise MathContractError("MathStepProposal.operation must be typed")
        if self.branch_id != MATH_BRANCH_ID:
            raise MathContractError(
                f"CAS-Math v0.1 only admits branch_id {MATH_BRANCH_ID!r}"
            )
        if self.theory_id != MATH_THEORY_ID:
            raise MathContractError(
                f"CAS-Math v0.1 only admits theory_id {MATH_THEORY_ID!r}"
            )
        if (
            not isinstance(self.premise_claim_ids, tuple)
            or len(self.premise_claim_ids) != len(set(self.premise_claim_ids))
            or len(self.premise_claim_ids) > MATH_MAX_PREMISES
            or any(
                not isinstance(item, str)
                or re.fullmatch(r"math-claim-[0-9a-f]{16}", item) is None
                for item in self.premise_claim_ids
            )
        ):
            raise MathContractError(
                "MathStepProposal.premise_claim_ids must be unique claim identifiers"
            )
        if (
            not self.premise_claim_ids
            and self.operation is not MathStepOperation.EVALUATE_EXACT
        ):
            raise MathContractError(f"{self.operation.value} requires at least one premise")
        if not isinstance(self.proposed_conclusion, MathStatement):
            raise MathContractError("MathStepProposal.proposed_conclusion must be typed")
        if self.parameter is not None:
            _require_expression(self.parameter, "MathStepProposal.parameter")
        if (
            not isinstance(self.substitutions, tuple)
            or self.substitutions != tuple(sorted(self.substitutions, key=lambda item: item[0]))
            or len({item[0] for item in self.substitutions}) != len(self.substitutions)
        ):
            raise MathContractError("MathStepProposal.substitutions must be sorted and unique")
        for name, expression in self.substitutions:
            _symbol(name, "MathStepProposal.substitution name")
            _require_expression(expression, "MathStepProposal.substitution expression")
        body = {
            "operation": self.operation.value,
            "premise_claim_ids": list(self.premise_claim_ids),
            "proposed_conclusion": self.proposed_conclusion.to_dict(),
            "parameter": (
                expression_to_dict(self.parameter) if self.parameter is not None else None
            ),
            "substitutions": [
                [name, expression_to_dict(expression)]
                for name, expression in self.substitutions
            ],
            "branch_id": self.branch_id,
            "theory_id": self.theory_id,
        }
        if self.proposal_id != content_id("math-proposal", body):
            raise MathContractError("MathStepProposal.proposal_id is not content-derived")

    @classmethod
    def create(
        cls,
        *,
        operation: MathStepOperation,
        premise_claim_ids: Iterable[str],
        proposed_conclusion: MathStatement,
        parameter: MathExpression | None = None,
        substitutions: Mapping[str, MathExpression] | None = None,
        branch_id: str = MATH_BRANCH_ID,
        theory_id: str = MATH_THEORY_ID,
    ) -> "MathStepProposal":
        if not isinstance(operation, MathStepOperation):
            raise MathContractError("MathStepProposal.operation must be typed")
        if branch_id != MATH_BRANCH_ID:
            raise MathContractError(
                f"CAS-Math v0.1 only admits branch_id {MATH_BRANCH_ID!r}"
            )
        if theory_id != MATH_THEORY_ID:
            raise MathContractError(
                f"CAS-Math v0.1 only admits theory_id {MATH_THEORY_ID!r}"
            )
        premises = tuple(premise_claim_ids)
        if any(
            not isinstance(item, str)
            or re.fullmatch(r"math-claim-[0-9a-f]{16}", item) is None
            for item in premises
        ):
            raise MathContractError(
                "premise_claim_ids must contain content-derived claim identifiers"
            )
        if not premises and operation not in {MathStepOperation.EVALUATE_EXACT}:
            raise MathContractError(f"{operation.value} requires at least one premise")
        if len(premises) != len(set(premises)):
            raise MathContractError("premise_claim_ids must be unique")
        if len(premises) > MATH_MAX_PREMISES:
            raise MathContractError(
                f"premise_claim_ids exceeds the {MATH_MAX_PREMISES}-premise limit"
            )
        if substitutions is not None and not isinstance(substitutions, Mapping):
            raise MathContractError("substitutions must be a mapping")
        raw_replacements = tuple((substitutions or {}).items())
        for name, expression in raw_replacements:
            _symbol(name, "MathStepProposal.substitution name")
            _require_expression(expression, "MathStepProposal.substitution expression")
        replacement_items = tuple(sorted(raw_replacements, key=lambda item: item[0]))
        for name, expression in replacement_items:
            _symbol(name, "MathStepProposal.substitution name")
            _require_expression(expression, "MathStepProposal.substitution expression")
        if parameter is not None:
            _require_expression(parameter, "MathStepProposal.parameter")
        body = {
            "operation": operation.value,
            "premise_claim_ids": list(premises),
            "proposed_conclusion": proposed_conclusion.to_dict(),
            "parameter": expression_to_dict(parameter) if parameter is not None else None,
            "substitutions": [
                [name, expression_to_dict(expression)] for name, expression in replacement_items
            ],
            "branch_id": branch_id,
            "theory_id": theory_id,
        }
        return cls(
            content_id("math-proposal", body),
            operation,
            premises,
            proposed_conclusion,
            parameter,
            replacement_items,
            branch_id,
            theory_id,
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MathStepProposal":
        _strict_keys(
            data,
            {
                "proposal_id",
                "operation",
                "premise_claim_ids",
                "proposed_conclusion",
                "parameter",
                "substitutions",
                "branch_id",
                "theory_id",
            },
            set(),
            "MathStepProposal",
        )
        try:
            operation = MathStepOperation(data["operation"])
        except (TypeError, ValueError) as exc:
            raise MathContractError("unsupported math step operation") from exc
        premises = data["premise_claim_ids"]
        substitutions = data["substitutions"]
        if not isinstance(premises, list) or any(not isinstance(item, str) for item in premises):
            raise MathContractError("premise_claim_ids must be a list of strings")
        if (
            not isinstance(substitutions, list)
            or any(not isinstance(item, list) or len(item) != 2 or not isinstance(item[0], str) for item in substitutions)
        ):
            raise MathContractError("substitutions must be name/expression pairs")
        if len({item[0] for item in substitutions}) != len(substitutions):
            raise MathContractError("substitution names must be unique")
        parameter_raw = data["parameter"]
        rebuilt = cls.create(
            operation=operation,
            premise_claim_ids=premises,
            proposed_conclusion=MathStatement.from_dict(data["proposed_conclusion"]),
            parameter=expression_from_dict(parameter_raw) if parameter_raw is not None else None,
            substitutions={item[0]: expression_from_dict(item[1]) for item in substitutions},
            branch_id=_symbol(data["branch_id"], "MathStepProposal.branch_id"),
            theory_id=_nonempty(data["theory_id"], "MathStepProposal.theory_id"),
        )
        if data["proposal_id"] != rebuilt.proposal_id:
            raise MathContractError("MathStepProposal.proposal_id is not content-derived")
        return rebuilt

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "operation": self.operation.value,
            "premise_claim_ids": list(self.premise_claim_ids),
            "proposed_conclusion": self.proposed_conclusion.to_dict(),
            "parameter": expression_to_dict(self.parameter) if self.parameter is not None else None,
            "substitutions": [
                [name, expression_to_dict(expression)] for name, expression in self.substitutions
            ],
            "branch_id": self.branch_id,
            "theory_id": self.theory_id,
        }


class MathRejectionCode(str, Enum):
    NONE = "NONE"
    UNKNOWN_PREMISE = "UNKNOWN_PREMISE"
    THEORY_MISMATCH = "THEORY_MISMATCH"
    UNVERIFIED_PREMISE = "UNVERIFIED_PREMISE"
    WRONG_PREMISE_COUNT = "WRONG_PREMISE_COUNT"
    MALFORMED_PARAMETER = "MALFORMED_PARAMETER"
    INVALID_TRANSFORMATION = "INVALID_TRANSFORMATION"
    UNDISCHARGED_GUARD = "UNDISCHARGED_GUARD"
    NEEDS_CAPABILITY = "NEEDS_CAPABILITY"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"


@dataclass(frozen=True, slots=True)
class MathStepReceipt:
    receipt_id: str
    proposal_digest: str
    accepted: bool
    reconstructed_conclusion: MathStatement | None
    discharged_guards: tuple[str, ...]
    checker_version: str
    theory_id: str
    rejection_code: MathRejectionCode
    detail: str

    def __post_init__(self) -> None:
        if not isinstance(self.proposal_digest, str) or _SHA256.fullmatch(
            self.proposal_digest
        ) is None:
            raise MathContractError("MathStepReceipt.proposal_digest must be SHA-256")
        if not isinstance(self.accepted, bool):
            raise MathContractError("MathStepReceipt.accepted must be Boolean")
        if self.accepted != (self.rejection_code is MathRejectionCode.NONE):
            raise MathContractError("receipt acceptance and rejection code disagree")
        if self.accepted and not isinstance(self.reconstructed_conclusion, MathStatement):
            raise MathContractError("accepted receipt requires a reconstructed conclusion")
        if not self.accepted and self.reconstructed_conclusion is not None:
            raise MathContractError("rejected receipt cannot carry a reconstructed conclusion")
        if (
            not isinstance(self.discharged_guards, tuple)
            or self.discharged_guards != tuple(sorted(set(self.discharged_guards)))
            or any(not isinstance(item, str) or not item for item in self.discharged_guards)
        ):
            raise MathContractError("receipt guards must be sorted unique strings")
        if self.checker_version != MATH_CHECKER_VERSION:
            raise MathContractError(
                f"CAS-Math v0.1 only admits checker_version {MATH_CHECKER_VERSION!r}"
            )
        if self.theory_id != MATH_THEORY_ID:
            raise MathContractError(
                f"CAS-Math v0.1 only admits theory_id {MATH_THEORY_ID!r}"
            )
        if not isinstance(self.rejection_code, MathRejectionCode):
            raise MathContractError("MathStepReceipt.rejection_code must be typed")
        if not isinstance(self.detail, str):
            raise MathContractError("MathStepReceipt.detail must be a string")
        body = {
            "proposal_digest": self.proposal_digest,
            "accepted": self.accepted,
            "reconstructed_conclusion": (
                self.reconstructed_conclusion.to_dict()
                if self.reconstructed_conclusion is not None
                else None
            ),
            "discharged_guards": list(self.discharged_guards),
            "checker_version": self.checker_version,
            "theory_id": self.theory_id,
            "rejection_code": self.rejection_code.value,
            "detail": self.detail,
        }
        if self.receipt_id != content_id("math-receipt", body):
            raise MathContractError("MathStepReceipt.receipt_id is not content-derived")

    @classmethod
    def create(
        cls,
        *,
        proposal: MathStepProposal,
        accepted: bool,
        reconstructed_conclusion: MathStatement | None,
        discharged_guards: Iterable[str] = (),
        rejection_code: MathRejectionCode = MathRejectionCode.NONE,
        detail: str = "",
        checker_version: str = MATH_CHECKER_VERSION,
    ) -> "MathStepReceipt":
        if not isinstance(proposal, MathStepProposal):
            raise MathContractError("receipt proposal must be a typed MathStepProposal")
        if checker_version != MATH_CHECKER_VERSION:
            raise MathContractError(
                f"CAS-Math v0.1 only admits checker_version {MATH_CHECKER_VERSION!r}"
            )
        if accepted != (rejection_code is MathRejectionCode.NONE):
            raise MathContractError("receipt acceptance and rejection code disagree")
        if accepted and reconstructed_conclusion is None:
            raise MathContractError("accepted receipt requires a reconstructed conclusion")
        if not accepted and reconstructed_conclusion is not None:
            raise MathContractError("rejected receipt cannot carry a reconstructed conclusion")
        guards = tuple(sorted(set(discharged_guards)))
        proposal_digest = digest(proposal.to_dict())
        body = {
            "proposal_digest": proposal_digest,
            "accepted": accepted,
            "reconstructed_conclusion": (
                reconstructed_conclusion.to_dict() if reconstructed_conclusion is not None else None
            ),
            "discharged_guards": list(guards),
            "checker_version": checker_version,
            "theory_id": proposal.theory_id,
            "rejection_code": rejection_code.value,
            "detail": detail,
        }
        return cls(
            content_id("math-receipt", body),
            proposal_digest,
            accepted,
            reconstructed_conclusion,
            guards,
            checker_version,
            proposal.theory_id,
            rejection_code,
            detail,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "proposal_digest": self.proposal_digest,
            "accepted": self.accepted,
            "reconstructed_conclusion": (
                self.reconstructed_conclusion.to_dict()
                if self.reconstructed_conclusion is not None
                else None
            ),
            "discharged_guards": list(self.discharged_guards),
            "checker_version": self.checker_version,
            "theory_id": self.theory_id,
            "rejection_code": self.rejection_code.value,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class MathParseLimits:
    max_characters: int = 4096
    max_tokens: int = 1024
    max_nodes: int = 4096
    max_depth: int = 64
    max_integer_digits: int = 256

    def __post_init__(self) -> None:
        for name in (
            "max_characters",
            "max_tokens",
            "max_nodes",
            "max_depth",
            "max_integer_digits",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise MathContractError(f"{name} must be a positive integer")


@dataclass(frozen=True, slots=True)
class CounterexampleBounds:
    variable: str
    lower: int
    upper: int

    def __post_init__(self) -> None:
        _symbol(self.variable, "CounterexampleBounds.variable")
        _strict_int(self.lower, "CounterexampleBounds.lower")
        _strict_int(self.upper, "CounterexampleBounds.upper")
        if self.lower > self.upper:
            raise MathContractError("counterexample lower bound exceeds upper bound")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CounterexampleBounds":
        _strict_keys(data, {"variable", "lower", "upper"}, set(), "CounterexampleBounds")
        return cls(
            _symbol(data["variable"], "CounterexampleBounds.variable"),
            _strict_int(data["lower"], "CounterexampleBounds.lower"),
            _strict_int(data["upper"], "CounterexampleBounds.upper"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"variable": self.variable, "lower": self.lower, "upper": self.upper}


def validate_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise MathContractError(f"{label} must be a lowercase SHA-256")
    return value
