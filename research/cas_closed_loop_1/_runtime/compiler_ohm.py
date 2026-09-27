"""CAS-Ohm arithmetic on explicitly declared coherent ratio scales.

This calculation convention is not a book calibration, a measurement system,
a circuit simulator, or a controller. No clamping, epsilon denominator, gain,
normalization or domain-drop extension is implicit.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Context, Decimal, DivisionByZero, InvalidOperation, Overflow, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
import hashlib
import json
import math
import re

VERSION = "cas.ohm.declared-linear/0.1"
MAX_DECIMAL_CHARS = 512
MAX_VALUE_BITS = 4096
MAX_LINEAGE_DEPTH = 16
MAX_LINEAGE_NODES = 256
_DECIMAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\Z")
QUANTITIES = frozenset(("drive", "attention", "constraint"))


class CasOhmError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(f"{code}: {message}")


def _text(value, label, limit=256):
    if type(value) is not str or not value.strip() or len(value) > limit:
        raise CasOhmError("OHM_METADATA", f"{label} must be nonempty text of at most {limit} characters")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise CasOhmError("OHM_METADATA", f"{label} must not contain control characters")
    return value


def _bounded(value):
    if type(value) is not Fraction or value < 0:
        raise CasOhmError("OHM_NUMBER", "quantities must be nonnegative rational values")
    if max(value.numerator.bit_length(), value.denominator.bit_length()) > MAX_VALUE_BITS:
        raise CasOhmError("OHM_LIMIT", "exact numeric result exceeds the 4096-bit budget")
    return value


def _integer_text(value):
    # Decimal's exact integer conversion does not inherit Python's configurable
    # int-to-string digit limit. Value size is bounded separately above.
    return format(Decimal(value), "f")


def _number(value):
    if type(value) is bool or value is None:
        raise CasOhmError("OHM_NUMBER", "a finite nonnegative number is required; missing values and booleans are invalid")
    if type(value) is str:
        if len(value) > MAX_DECIMAL_CHARS:
            raise CasOhmError("OHM_LIMIT", "decimal input exceeds 512 characters")
        if not _DECIMAL.fullmatch(value):
            raise CasOhmError("OHM_NUMBER", "supply a finite decimal, without exponent notation")
        exact = Fraction(value)
        representation = "exact_decimal_text"
        literal = value
    elif type(value) is int:
        if value.bit_length() > MAX_VALUE_BITS:
            raise CasOhmError("OHM_LIMIT", "integer input exceeds the numeric budget")
        exact, representation, literal = Fraction(value), "integer", _integer_text(value)
    elif type(value) is float:
        if not math.isfinite(value):
            raise CasOhmError("OHM_NUMBER", "NaN and infinity are invalid")
        literal = str(value)
        exact, representation = Fraction(literal), "binary_float_via_shortest_decimal"
    else:
        raise CasOhmError("OHM_NUMBER", "supply an integer, finite float, or exact decimal string")
    return _bounded(exact), representation, literal


def _number_record(value):
    context = Context(prec=40, rounding=ROUND_HALF_EVEN, Emin=-9999, Emax=9999,
                      capitals=1, clamp=0, flags=[], traps=[InvalidOperation, DivisionByZero, Overflow])
    with localcontext(context):
        decimal = Decimal(value.numerator) / Decimal(value.denominator)
    return {
        "value": str(decimal),
        "exact_value": {"numerator": _integer_text(value.numerator), "denominator": _integer_text(value.denominator)},
        "decimal_is_rounded": Fraction(decimal) != value,
    }


def _digest(value):
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class OhmScale:
    id: str
    drive_unit: str
    attention_unit: str

    def __post_init__(self):
        _text(self.id, "scale id", 128)
        _text(self.drive_unit, "Drive unit", 128)
        _text(self.attention_unit, "attention unit", 128)

    def to_dict(self):
        descriptor = {
            "kind": "cas_ohm_scale", "convention": VERSION, "id": self.id,
            "drive_unit": self.drive_unit, "attention_unit": self.attention_unit,
            "constraint_unit": f"({self.drive_unit})/({self.attention_unit})",
            "status": "USER_DECLARED_COHERENT_RATIO_SCALE",
            "calibration_status": "NOT_VERIFIED",
        }
        return {**descriptor, "descriptor_sha256": _digest(descriptor)}


@dataclass(frozen=True, slots=True)
class OhmQuantity:
    quantity: str
    value: Fraction
    scale: OhmScale
    origin: str
    reference: str
    representation: str
    literal: str | None = None
    operation: str | None = None
    inputs: tuple[OhmQuantity, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self):
        if type(self.quantity) is not str or self.quantity not in QUANTITIES:
            raise CasOhmError("OHM_KIND", "unknown quantity kind")
        _bounded(self.value)
        if type(self.scale) is not OhmScale:
            raise CasOhmError("OHM_SCALE", "an explicit OhmScale is required")
        if self.origin not in ("design", "supplied_observation", "calculated"):
            raise CasOhmError("OHM_ORIGIN", "unknown quantity origin")
        _text(self.reference, "source/reference")
        if type(self.inputs) is not tuple or any(type(item) is not OhmQuantity for item in self.inputs):
            raise CasOhmError("OHM_PROVENANCE", "calculation inputs must be typed quantities")
        if type(self.notes) is not tuple or any(type(note) is not str for note in self.notes):
            raise CasOhmError("OHM_PROVENANCE", "notes must be a tuple of text labels")
        if self.origin == "calculated":
            if self.operation not in ("attention_flow", "required_drive", "effective_constraint") or len(self.inputs) != 2:
                raise CasOhmError("OHM_PROVENANCE", "calculated quantities require their operation and two inputs")
            left, right = self.inputs
            expected = {
                "attention_flow": ("drive", "constraint", "attention"),
                "required_drive": ("attention", "constraint", "drive"),
                "effective_constraint": ("drive", "attention", "constraint"),
            }[self.operation]
            _operands(left, right, expected[:2])
            if self.quantity != expected[2] or self.scale != left.scale:
                raise CasOhmError("OHM_PROVENANCE", "result kind and scale must follow its inputs")
            if self.operation != "required_drive" and right.value == 0:
                raise CasOhmError("OHM_PROVENANCE", "derived provenance has a zero denominator")
            calculated = left.value * right.value if self.operation == "required_drive" else left.value / right.value
            if self.value != calculated or self.representation != "exact_rational" or self.literal is not None:
                raise CasOhmError("OHM_PROVENANCE", "derived value must equal the recorded exact operation")
            expected_notes = []
            if self.operation == "required_drive" and (left.value == 0 or right.value == 0):
                expected_notes.append("ZERO_FACTOR_DEGENERATE_DESIGN")
            if self.operation == "effective_constraint":
                expected_notes.append("INVERSE_RATIO_NOT_CAUSAL_IDENTIFICATION")
                if left.value == 0:
                    expected_notes.append("ZERO_CONSTRAINT_DEGENERATE_RATIO")
            if self.notes != tuple(expected_notes) or self.reference != f"{VERSION}:{self.operation}":
                raise CasOhmError("OHM_PROVENANCE", "derived notes and reference must identify the declared calculation")
        elif self.operation is not None or self.inputs:
            raise CasOhmError("OHM_PROVENANCE", "input declarations cannot carry a calculation")
        else:
            if type(self.literal) is not str or self.notes:
                raise CasOhmError("OHM_PROVENANCE", "input declarations require their numeric literal and no derived notes")
            if self.representation == "exact_decimal_text":
                declared = _number(self.literal)[0]
            elif self.representation == "integer":
                if len(self.literal) > 1235 or not re.fullmatch(r"-?[0-9]+", self.literal):
                    raise CasOhmError("OHM_PROVENANCE", "invalid integer source literal")
                declared = _number(int(Decimal(self.literal)))[0]
                if _integer_text(int(Decimal(self.literal))) != self.literal:
                    raise CasOhmError("OHM_PROVENANCE", "integer source literal is not canonical")
            elif self.representation == "binary_float_via_shortest_decimal":
                if len(self.literal) > 32:
                    raise CasOhmError("OHM_PROVENANCE", "invalid float source literal")
                try:
                    floating = float(self.literal)
                except ValueError as error:
                    raise CasOhmError("OHM_PROVENANCE", "invalid float source literal") from error
                declared = _number(floating)[0]
                if str(floating) != self.literal:
                    raise CasOhmError("OHM_PROVENANCE", "float source literal is not canonical")
            else:
                raise CasOhmError("OHM_PROVENANCE", "unknown input numeric representation")
            if declared != self.value:
                raise CasOhmError("OHM_PROVENANCE", "declared value differs from its recorded input literal")
        if self.depth > MAX_LINEAGE_DEPTH or self.node_count > MAX_LINEAGE_NODES:
            raise CasOhmError("OHM_LIMIT", "calculation lineage exceeds the depth/node budget")

    @property
    def depth(self):
        return 1 + max((item.depth for item in self.inputs), default=0)

    @property
    def node_count(self):
        return 1 + sum(item.node_count for item in self.inputs)

    def to_dict(self):
        scale = self.scale.to_dict()
        unit = {
            "drive": self.scale.drive_unit, "attention": self.scale.attention_unit,
            "constraint": scale["constraint_unit"],
        }[self.quantity]
        record = {
            "kind": "cas_ohm_quantity", "convention": VERSION,
            "quantity": self.quantity, **_number_record(self.value), "unit": unit,
            "scale": scale, "origin": self.origin, "reference": self.reference,
            "numeric_representation": self.representation, "input_literal": self.literal,
            "operation": self.operation, "inputs": [item.to_dict() for item in self.inputs],
            "notes": list(self.notes),
            "measurement_status": "NO_MEASUREMENT_PERFORMED",
            "observation_status": "CALLER_SUPPLIED_UNVERIFIED" if self.origin == "supplied_observation" else "NOT_AN_OBSERVATION",
            "control_status": "NOT_CONNECTED", "semantic_outcome": "NOT_ASSESSED",
        }
        return {**record, "record_sha256": _digest(record)}


def make_scale(id, drive_unit, attention_unit):
    """Declare coherent units; never silently select a canonical calibration."""
    return OhmScale(id, drive_unit, attention_unit)


def make_quantity(kind, value, scale, origin, reference):
    """An observation declaration is a claim by the caller, not a sensor read."""
    if origin not in ("design", "supplied_observation"):
        raise CasOhmError("OHM_ORIGIN", "input origin must be design or supplied_observation; calculated is reserved for operation results")
    exact, representation, literal = _number(value)
    return OhmQuantity(kind, exact, scale, origin, reference, representation, literal)


def _operands(left, right, expected):
    if type(left) is not OhmQuantity or type(right) is not OhmQuantity:
        raise CasOhmError("OHM_KIND", "operations require typed CAS-Ohm quantities")
    if (left.quantity, right.quantity) != expected:
        raise CasOhmError("OHM_KIND", f"expected {expected[0]} then {expected[1]}")
    if left.scale != right.scale:
        raise CasOhmError("OHM_SCALE_MISMATCH", "complete scale descriptors must match; no automatic conversion is defined")
    _bounded(left.value)
    _bounded(right.value)


def _result(kind, value, left, right, operation, notes=()):
    return OhmQuantity(kind, _bounded(value), left.scale, "calculated",
                       f"{VERSION}:{operation}", "exact_rational",
                       operation=operation, inputs=(left, right), notes=notes)


def attention_flow(drive, constraint):
    """I = V/R. A zero denominator is refused even when V is also zero."""
    _operands(drive, constraint, ("drive", "constraint"))
    if constraint.value == 0:
        raise CasOhmError("OHM_ZERO_CONSTRAINT", "attention flow is undefined for zero constraint")
    return _result("attention", drive.value / constraint.value, drive, constraint, "attention_flow")


def required_drive(attention, constraint):
    """V = I*R. Zero factors are retained as algebraic design degeneracies."""
    _operands(attention, constraint, ("attention", "constraint"))
    notes = ("ZERO_FACTOR_DEGENERATE_DESIGN",) if attention.value == 0 or constraint.value == 0 else ()
    return _result("drive", attention.value * constraint.value, attention, constraint, "required_drive", notes)


def effective_constraint(drive, attention):
    """R = V/I. This inverse ratio does not identify causal hidden resistance."""
    _operands(drive, attention, ("drive", "attention"))
    if attention.value == 0:
        raise CasOhmError("OHM_ZERO_ATTENTION", "effective constraint is undefined for zero attention")
    notes = ["INVERSE_RATIO_NOT_CAUSAL_IDENTIFICATION"]
    if drive.value == 0:
        notes.append("ZERO_CONSTRAINT_DEGENERATE_RATIO")
    return _result("constraint", drive.value / attention.value, drive, attention, "effective_constraint", tuple(notes))
