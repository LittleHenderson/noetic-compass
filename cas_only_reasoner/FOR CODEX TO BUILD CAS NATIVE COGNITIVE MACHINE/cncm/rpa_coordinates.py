"""Bounded, present-centered CAS-RPA coordinates for declared profiles.

Atlas v0.1 pp. 6-7, 20-21 defines the label order and centered additive
log-ratio chart. PDF SHA-256:
e1acd28bbdc91e5b33e1f29f2610e75b80960dc55b6907b1dc34311a3a6386ab.
The inverse is derived in docs/CAS_RPA_MATHEMATICAL_REVIEW.md.

Exact profile validation precedes approximate binary64 display arithmetic.
No source, observation, reference identity, or calibration is inferred here.
This chart is neither a distance metric nor a probability of future outcomes.
"""
from __future__ import annotations

from fractions import Fraction
import math
import sys

from .model import ContractError
from .rpa_model import validate_profile40

CANONICAL_ORDER = "^0..^9 x P,C,E,O; row-major"
DOMAIN_MAJOR_ORDER = "P,C,E,O x ^0..^9; domain-major"
CANONICAL_LABELS = tuple(f"^{noetic}/{domain}" for noetic in range(10) for domain in ("P", "C", "E", "O"))
# The only alternate order is cncm.noetica.COGNITIVE_STATES: P0..P9,
# C0..C9, E0..E9, O0..O9. This permutes identical labels; it does not map
# Domains to Registers, Drives, Foundations, or Capability Pathways.
DOMAIN_MAJOR_LABELS = tuple(f"^{noetic}/{domain}" for domain in ("P", "C", "E", "O") for noetic in range(10))
COORDINATE_LABELS = CANONICAL_LABELS[:-1]
DENOMINATOR_LABEL = CANONICAL_LABELS[-1]
ROUND_TRIP_REL_TOL = 5e-13
ROUND_TRIP_ABS_TOL = 0.0
COORDINATE_ABS_TOL = 2e-13
NORMALIZATION_ABS_TOL = 2e-15
NUMERICAL_POLICY = {
    "schema_version": "cas.rpa.centered-alr/0.1",
    "profile_input": "forty canonical positive rational strings; exact sum one; 128-bit integers",
    "coordinate_output": "39 approximate binary64 natural log ratios in canonical order",
    "inverse_output": "40 approximate binary64 components; not an exact recorded profile",
    "denominator_label": DENOMINATOR_LABEL,
    "reference_rule": "explicit supplied profile; no uniform default",
    "round_trip_relative_tolerance": ROUND_TRIP_REL_TOL,
    "round_trip_absolute_tolerance": ROUND_TRIP_ABS_TOL,
    "coordinate_absolute_tolerance": COORDINATE_ABS_TOL,
    "normalization_absolute_tolerance": NORMALIZATION_ABS_TOL,
    "minimum_inverse_component": sys.float_info.min,
    "boundary_policy": "reject zero, subnormal, nonfinite, or rounded-to-one inverse components; no clipping or imputation",
    "metric_status": "CHART_ONLY_NOT_FISHER_RAO_OR_TRANSITION_COST",
    "measurement_status": "NO_MEASUREMENT_PERFORMED",
}


def _require(condition, message):
    if not condition:
        raise ContractError(message)


def _labels(order):
    _require(type(order) is str, "profile order must be an explicit known string")
    if order == CANONICAL_ORDER:
        return CANONICAL_LABELS
    if order == DOMAIN_MAJOR_ORDER:
        return DOMAIN_MAJOR_LABELS
    raise ContractError("unknown profile order; no namespace crosswalk is inferred")


def validate_profile(profile):
    """Return exact fractions; refuse absent, zero, rounded, or partial input.

    The existing bounded profile contract is reused unchanged. Its required
    basis text below identifies this validation operation, not source evidence;
    source/basis metadata belongs to the calling atlas bundle.
    """
    _require(profile is not None, "coordinate profile is not assigned")
    validate_profile40(profile, "coordinate arithmetic validation only")
    return tuple(Fraction(value) for value in profile)


def reorder_profile(profile, *, source_order, target_order):
    """Permute an exact profile between the two named orders without mutation."""
    source, target = _labels(source_order), _labels(target_order)
    validate_profile(profile)
    positions = {label: index for index, label in enumerate(source)}
    return tuple(profile[positions[label]] for label in target)


def _canonical_values(profile, order):
    return tuple(Fraction(value) for value in reorder_profile(
        profile, source_order=order, target_order=CANONICAL_ORDER))


def _log_ratio(value):
    # Form the ratio exactly first. log1p preserves small changes that would
    # disappear if a near-one rational were rounded to float before logging.
    if Fraction(1, 2) <= value <= Fraction(3, 2):
        return math.log1p(float(value - 1))
    return math.log(float(value))


def centered_coordinates(profile, reference, *, profile_order, reference_order):
    """Return z_i = log(p_i/p_40) - log(ref_i/ref_40), i=1..39.

    The equivalent log(p_i/ref_i)-log(p_40/ref_40) uses bounded exact ratios
    before logging and maps a supplied profile to its own origin exactly.
    Results always follow COORDINATE_LABELS, regardless of either input order.
    """
    values = _canonical_values(profile, profile_order)
    ref = _canonical_values(reference, reference_order)
    offset = _log_ratio(values[-1] / ref[-1])
    result = tuple(_log_ratio(value / baseline) - offset for value, baseline in zip(values[:-1], ref[:-1]))
    _require(all(math.isfinite(value) for value in result), "coordinate result is not finite")
    return result


def _coordinate_values(coordinates):
    _require(type(coordinates) is tuple and len(coordinates) == 39,
             "centered coordinates need exactly thirty-nine values in a tuple")
    result = []
    for value in coordinates:
        _require(type(value) in (int, float), "centered coordinate must be a finite number, not bool or text")
        _require(type(value) is not int or value.bit_length() <= 1023,
                 "centered coordinate integer bound exceeded")
        number = float(value)
        _require(math.isfinite(number), "centered coordinate is not finite")
        result.append(number)
    return tuple(result)


def recover_profile(coordinates, reference, *, reference_order, output_order):
    """Invert the chart using its actual reference; return display floats.

    log(ref_i)+z_i (with z_40=0) is normalized by log-sum-exp. Inputs that
    cannot produce an interior normal-binary64 profile are refused, rather
    than replacing a small component by zero, clipping it, or adding epsilon.
    No approximate output is promoted into the exact profile input contract.
    """
    target = _labels(output_order)
    ref = _canonical_values(reference, reference_order)
    z = _coordinate_values(coordinates)
    if all(value == 0.0 for value in z):
        # Preserve the actual reference at the origin, including nonuniformity.
        result = tuple(float(value) for value in ref)
    else:
        logs = tuple(math.log(float(value)) + shift for value, shift in zip(ref, z + (0.0,)))
        _require(all(math.isfinite(value) for value in logs), "inverse log weights are not finite")
        maximum = max(logs)
        differences = tuple(value - maximum for value in logs)
        _require(all(math.isfinite(value) for value in differences), "inverse log-weight spread is not representable")
        minimum_log = math.log(sys.float_info.min)
        _require(all(value >= minimum_log for value in differences), "inverse would underflow the positive profile boundary")
        weights = tuple(math.exp(value) for value in differences)
        total = math.fsum(weights)
        result = tuple(value / total for value in weights)
    _require(all(math.isfinite(value) and sys.float_info.min <= value < 1.0 for value in result),
             "inverse profile reaches an unrepresentable or underflowed boundary")
    _require(math.isclose(math.fsum(result), 1.0, rel_tol=0.0, abs_tol=NORMALIZATION_ABS_TOL),
             "inverse normalization exceeds numerical tolerance")
    positions = {label: index for index, label in enumerate(CANONICAL_LABELS)}
    return tuple(result[positions[label]] for label in target)
