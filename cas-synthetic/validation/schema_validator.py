"""Schema validator for data_format.md.

Checks the per-example fields required / optional / type-constrained by the
authoritative schema. Implemented directly (no jsonschema dep required) so
the scaffold runs against stock Python.

Invariants enforced (per data_format.md §Invariants):
  1. prompt and response are non-empty strings.
  2. Every `register` value is in {"T", "A", "f", "E"} (lowercase f).
  3. Every `omega_name` is non-empty (admission check lives in composite).
  4. Every `prereqs` / `leakages` `state_id` is in [0, 40).
  5. Every `coefficient` is a strictly positive float.
  6. `observed_yield` is a non-negative float.
  7. `scores.operator_scores` has length 10 (if present).
  8. `scores.domain_scores` has length 4 (if present).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class SchemaValidationError(ValueError):
    """Raised when an example fails schema validation."""


CANONICAL_REGISTERS = {"T", "A", "f", "E"}


@dataclass
class SchemaValidator:
    """Validates one dict-shaped training example at a time."""

    strict: bool = True

    def validate(self, example: dict[str, Any]) -> list[str]:
        """Return a list of error strings; empty list = passed.

        If `strict=True` and errors are found, raises SchemaValidationError.
        """
        errors: list[str] = []

        # required fields
        prompt = example.get("prompt")
        response = example.get("response")
        if not isinstance(prompt, str) or not prompt:
            errors.append("prompt must be a non-empty string")
        if not isinstance(response, str) or not response:
            errors.append("response must be a non-empty string")

        # scores — optional, but if present must be correct shape
        scores = example.get("scores")
        if scores is not None:
            if not isinstance(scores, dict):
                errors.append("scores must be a dict when present")
            else:
                op = scores.get("operator_scores")
                if op is not None:
                    if not isinstance(op, list) or len(op) != 10:
                        errors.append("scores.operator_scores must be a length-10 list")
                    else:
                        for i, v in enumerate(op):
                            if not isinstance(v, (int, float)):
                                errors.append(f"scores.operator_scores[{i}] must be a number")
                dom = scores.get("domain_scores")
                if dom is not None:
                    if not isinstance(dom, list) or len(dom) != 4:
                        errors.append("scores.domain_scores must be a length-4 list")
                    else:
                        for i, v in enumerate(dom):
                            if not isinstance(v, (int, float)):
                                errors.append(f"scores.domain_scores[{i}] must be a number")

        # register_labels
        register_labels = example.get("register_labels", [])
        if register_labels is not None and not isinstance(register_labels, list):
            errors.append("register_labels must be a list when present")
        else:
            for i, lbl in enumerate(register_labels or []):
                if not isinstance(lbl, dict):
                    errors.append(f"register_labels[{i}] must be a dict")
                    continue
                pos = lbl.get("position")
                reg = lbl.get("register")
                if not isinstance(pos, int):
                    errors.append(f"register_labels[{i}].position must be int")
                if not isinstance(reg, str) or reg not in CANONICAL_REGISTERS:
                    errors.append(
                        f"register_labels[{i}].register must be one of {sorted(CANONICAL_REGISTERS)} "
                        f"(got {reg!r})"
                    )

        # omega_labels
        omega_labels = example.get("omega_labels", [])
        if omega_labels is not None and not isinstance(omega_labels, list):
            errors.append("omega_labels must be a list when present")
        else:
            for i, lbl in enumerate(omega_labels or []):
                if not isinstance(lbl, dict):
                    errors.append(f"omega_labels[{i}] must be a dict")
                    continue
                if not isinstance(lbl.get("position"), int):
                    errors.append(f"omega_labels[{i}].position must be int")
                name = lbl.get("omega_name")
                if not isinstance(name, str) or not name:
                    errors.append(f"omega_labels[{i}].omega_name must be a non-empty string")

        # production_target
        pt = example.get("production_target")
        if pt is not None:
            if not isinstance(pt, dict):
                errors.append("production_target must be a dict when present")
            else:
                prereqs = pt.get("prereqs")
                if not isinstance(prereqs, list) or not prereqs:
                    errors.append("production_target.prereqs must be a non-empty list")
                else:
                    for i, pair in enumerate(prereqs):
                        if (
                            not isinstance(pair, (list, tuple))
                            or len(pair) != 2
                        ):
                            errors.append(
                                f"production_target.prereqs[{i}] must be a [state_id, coefficient] pair"
                            )
                            continue
                        sid, coef = pair
                        if not isinstance(sid, int) or not (0 <= sid < 40):
                            errors.append(
                                f"production_target.prereqs[{i}].state_id must be int in [0, 40)"
                            )
                        if not isinstance(coef, (int, float)) or coef <= 0:
                            errors.append(
                                f"production_target.prereqs[{i}].coefficient must be > 0"
                            )
                leakages = pt.get("leakages", [])
                if leakages is not None and not isinstance(leakages, list):
                    errors.append("production_target.leakages must be a list when present")
                else:
                    for i, pair in enumerate(leakages or []):
                        if (
                            not isinstance(pair, (list, tuple))
                            or len(pair) != 2
                        ):
                            errors.append(
                                f"production_target.leakages[{i}] must be a [state_id, magnitude] pair"
                            )
                            continue
                        sid, mag = pair
                        if not isinstance(sid, int) or not (0 <= sid < 40):
                            errors.append(
                                f"production_target.leakages[{i}].state_id must be int in [0, 40)"
                            )
                        if not isinstance(mag, (int, float)):
                            errors.append(
                                f"production_target.leakages[{i}].magnitude must be a number"
                            )
                oy = pt.get("observed_yield")
                if oy is not None and (not isinstance(oy, (int, float)) or oy < 0):
                    errors.append("production_target.observed_yield must be a non-negative number")

        if errors and self.strict:
            raise SchemaValidationError("; ".join(errors))
        return errors


def validate_example_schema(example: dict[str, Any]) -> list[str]:
    """Convenience: instantiate default validator and run."""
    return SchemaValidator(strict=False).validate(example)
