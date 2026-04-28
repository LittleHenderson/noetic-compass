"""Rust engine-backed validator via the vendored cas_engine wheel.

Uses the batch APIs on the wheel 0.1.1:
  - validate_same_noetic_cross_product_batch
  - rule_four_distance_batch
  - verify_named_emergent_register_batch
  - compute_yield_batch

When the vendored wheel is not importable, raises RustValidatorUnavailable
on construction so callers can gracefully fall back to schema + composite
checks only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

from .schema_validator import CANONICAL_REGISTERS


class RustValidatorUnavailable(RuntimeError):
    """Raised when the cas_engine wheel cannot be imported."""


_VENDOR_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "noetic-compass-scaffold"
    / "noetic-compass"
    / "cas-native"
    / "tests"
    / "_vendor"
)


def _ensure_cas_engine_importable() -> Any:
    """Insert vendor path and import cas_engine; raise on failure."""
    if str(_VENDOR_PATH) not in sys.path:
        sys.path.insert(0, str(_VENDOR_PATH))
    try:
        import cas_engine  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RustValidatorUnavailable(
            f"cas_engine wheel not importable at {_VENDOR_PATH}: {exc}"
        ) from exc
    required = (
        "validate_same_noetic_cross_product_batch",
        "rule_four_distance_batch",
        "verify_named_emergent_register_batch",
        "NamedEmergentRegister",
        "RegisterSet",
    )
    missing = [name for name in required if not hasattr(cas_engine, name)]
    if missing:
        raise RustValidatorUnavailable(
            "cas_engine wheel is importable but missing required Level 2 "
            f"bindings: {', '.join(missing)}"
        )
    return cas_engine


# Pattern matching operand instances inside a cas_expression string.
# Handles: ^N|R, ^N^D|R, ^N^D|R_{Fk}, and compiler state variants
# such as ^N^D_{Fk}|R.
_OPERAND_RE = re.compile(
    r"\^(\d+)(?:\^([PCEO]))?(?:_\{F(\d)\})?\|([TAfE])(?:_\{F(\d)\})?"
)

# Rule 4 relevant tokens: `x` (ASCII times) or `×` between operands.
_TIMES_TOKENS = (" x ", " × ")


class RustValidator:
    """Wrapper around the Rust engine batch API for Level 2 validation."""

    def __init__(self) -> None:
        self.cas_engine = _ensure_cas_engine_importable()

    # ------------------------------------------------------------- Rule 4

    def evaluate_rule_four(self, examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """For each example that contains a same-Noetic × expression, run the
        Rule 4 batch validator and return per-example results.

        Returns a list of dicts with keys:
          - applicable: bool
          - is_valid: bool (True if applicable and Rust says valid)
          - distance: float (0.0 if valid, positive severity if violation)
          - rust_kind: str (Rust's result.kind or "n/a")
        """
        ce = self.cas_engine

        batch_operands: list[tuple[list[tuple[int, int | None, int | None, str | None]], Any]] = []
        applicable_indices: list[int] = []

        for idx, ex in enumerate(examples):
            expr = ex.get("cas_expression", "")
            operands = self._parse_cross_product_operands(expr)
            if operands is None:
                continue
            tuples, emergent_name = operands
            named = ce.NamedEmergentRegister(emergent_name) if emergent_name else None
            batch_operands.append((tuples, named))
            applicable_indices.append(idx)

        results: list[dict[str, Any]] = [
            {"applicable": False, "is_valid": True, "distance": 0.0, "rust_kind": "n/a"}
            for _ in examples
        ]
        if not batch_operands:
            return results

        rule_four_results = ce.validate_same_noetic_cross_product_batch(batch_operands)
        distances = ce.rule_four_distance_batch(batch_operands)

        for idx, rf_result, dist in zip(applicable_indices, rule_four_results, distances):
            kind = str(getattr(rf_result, "kind", "n/a"))
            is_valid = "valid" in kind and "violation" not in kind
            results[idx] = {
                "applicable": True,
                "is_valid": bool(is_valid),
                "distance": float(dist),
                "rust_kind": kind,
            }
        return results

    # ------------------------------------------------- Named emergent verify

    def evaluate_named_emergent(
        self, examples: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """For each example carrying omega_labels AND register_labels, verify
        (RegisterSet, NamedEmergentRegister) pair via the Rust batch API.
        """
        ce = self.cas_engine
        batch: list[tuple[Any, Any]] = []
        applicable_indices: list[int] = []

        for idx, ex in enumerate(examples):
            omega_labels = ex.get("omega_labels", [])
            register_labels = ex.get("register_labels", [])
            if not omega_labels or not register_labels:
                continue
            registers = [lbl["register"] for lbl in register_labels if lbl.get("register") in CANONICAL_REGISTERS]
            if not registers:
                continue
            name = omega_labels[0].get("omega_name", "")
            if not name:
                continue
            rs = ce.RegisterSet(registers)
            ner = ce.NamedEmergentRegister(name)
            batch.append((rs, ner))
            applicable_indices.append(idx)

        results: list[dict[str, Any]] = [
            {"applicable": False, "is_valid": True, "rust_kind": "n/a"}
            for _ in examples
        ]
        if not batch:
            return results

        rust_results = ce.verify_named_emergent_register_batch(batch)
        for idx, r in zip(applicable_indices, rust_results):
            kind = str(getattr(r, "kind", "valid"))
            results[idx] = {
                "applicable": True,
                "is_valid": "valid" in kind and "invalid" not in kind,
                "rust_kind": kind,
            }
        return results

    # ------------------------------------------------------------ parsing

    def _parse_cross_product_operands(
        self, expression: str
    ) -> tuple[list[tuple[int, int | None, int | None, str | None]], str | None] | None:
        """Parse a cas_expression into operand tuples suitable for the Rust
        Rule 4 batch API, iff the expression contains a same-Noetic `x`
        cross product. Returns (operands, emergent_name or None) or None
        when the expression is not Rule 4 applicable.
        """
        if not any(tok in expression for tok in _TIMES_TOKENS):
            return None

        # Isolate the left-hand side (before any `=` sign, which holds the emergent name).
        emergent_name: str | None = None
        if "=" in expression:
            lhs, rhs = expression.split("=", 1)
            m = re.search(r"\|((?:Omega|Ω)_\w+)", rhs)
            if m:
                emergent_name = m.group(1)
            work = lhs
        else:
            work = expression

        matches = list(_OPERAND_RE.finditer(work))
        if len(matches) < 2:
            return None

        operands: list[tuple[int, int | None, int | None, str | None]] = []
        noetics_seen: set[int] = set()
        domain_map = {"P": 0, "C": 1, "E": 2, "O": 3}
        for m in matches:
            noetic = int(m.group(1))
            dom = m.group(2)
            drive_raw = m.group(3) or m.group(5)
            drive = int(drive_raw) if drive_raw else None
            reg = m.group(4)
            operands.append(
                (
                    noetic,
                    domain_map[dom] if dom else None,
                    drive,
                    reg,
                )
            )
            noetics_seen.add(noetic)

        # Rule 4 applies when same-Noetic × across multiple registers.
        if len(noetics_seen) != 1:
            return None

        return operands, emergent_name
