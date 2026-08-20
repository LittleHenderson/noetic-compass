"""7-axis Inversion Scan for the CAS-as-Belief-Substrate.

Authoritative axis catalogue (CLAUDE.md "7 Inversion Axes"):

* **N** — Operator / Noetic involution imbalance. Pairs CO-2↔CO-3, CO-5↔CO-6,
  CO-8↔CO-9. Self-duals CO-0/CO-1/CO-4/CO-7. A flag fires when the contradiction
  history shows a same-claim opposition without re-evaluation.
* **W** — Domain precedence violation. Total order P ≻ C ≻ E ≻ O. A flag fires
  when the claim's compiled type-domain is ``O`` (lowest) but the claim_text
  surfaces principled-language markers, or when the cas_expression mixes
  domains in a precedence-inverted way (we detect O-then-P sequencing in the
  source string as a v1 heuristic).
* **F** — Drive pair imbalance. Pairs F1↔F7, F2↔F6, F3↔F5. F4 self-dual. A
  flag fires if the cas_expression contains both members of an inversion pair
  with no integration operator (``+`` or ``×``) between them.
* **E** — State-vector entropy deficit. Placeholder — the v1 belief substrate
  does not run the Fisher-Rao entropy machinery. Returns ``clean=True`` with a
  ``placeholder=True`` marker so the structured output is honest about scope.
* **S** — Sub-Drive cross-domain variance. Placeholder — same rationale as E.
* **A** — Pathway RPM chain violation. Re-uses the RPM gate. If the RPM chain
  did NOT satisfy on the active belief, axis A flags.
* **P** — Compound. Fires when more than one of {N, W, F, A} has flagged.

The gate returns ``clean = (no axis flagged)``. Placeholder axes never flag in
v1; their advisory state is preserved in the per-axis dict.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable


# Authoritative pair tables (CLAUDE.md "Structural invariants").
NOETIC_INVOLUTION_PAIRS: dict[int, int] = {
    2: 3, 3: 2, 5: 6, 6: 5, 8: 9, 9: 8,
}
NOETIC_SELF_DUALS: frozenset[int] = frozenset({0, 1, 4, 7})

DOMAIN_PRECEDENCE: dict[str, int] = {"P": 0, "C": 1, "E": 2, "O": 3}

DRIVE_INVOLUTION_PAIRS: dict[int, int] = {
    1: 7, 7: 1, 2: 6, 6: 2, 3: 5, 5: 3,
}
DRIVE_SELF_DUALS: frozenset[int] = frozenset({4})

ALL_AXES: tuple[str, ...] = ("N", "W", "F", "E", "S", "A", "P")
PLACEHOLDER_AXES: tuple[str, ...] = ("E", "S")

# Persisted scan payloads are derived data.  This identity must change whenever
# extraction or verdict semantics change so BeliefStore can rescan old rows
# instead of silently reusing evidence produced by a different algorithm.
INVERSION_SCANNER_VERSION = "inversion_gate.v3.unicode_domain_marker_boundary"


@dataclass
class InversionScanResult:
    """Outcome of a 7-axis scan.

    `clean` is True iff every non-placeholder axis returned ``clean=True``.
    `axes` is keyed by axis letter; each value is a dict with at least a
    ``clean`` boolean and a ``reason`` string. Placeholder axes also include
    ``placeholder=True``.
    """

    clean: bool
    axes: dict[str, dict[str, Any]]


# ---------------------------------------------------------------------------
# Per-axis primitives
# ---------------------------------------------------------------------------


_NOETIC_RE = re.compile(r"\^([0-9])")
# NOTE (bug fix): this pattern previously ended in ``\b``. ``_`` is a word
# character, so in the drive-tagged literals this project actually emits —
# ``^8^E_{F5} -> ^6^C_{F5}`` — the boundary between ``E`` and ``_`` is NOT a
# word boundary and ``\b`` never matched. ``_extract_domains`` returned ``[]``
# and axis W could therefore NEVER fire on a drive-tagged expression. The
# Candidate matching is followed by a Unicode-aware boundary check in
# ``_extract_domains``.  ASCII-only ``[A-Za-z0-9]`` incorrectly accepted
# strings such as ``^Pé`` and ``^P١`` as a domain marker.  Underscore remains
# explicitly permitted because canonical drive tags begin ``_{F...}``.
_DOMAIN_RE = re.compile(r"\^([PCEO])")
_DRIVE_RE = re.compile(r"\bF([1-7])\b|F_?([1-7])")


def _extract_noetic_indices(expression: str) -> list[int]:
    return [int(m.group(1)) for m in _NOETIC_RE.finditer(expression)]


def _extract_domains(expression: str) -> list[str]:
    domains: list[str] = []
    for match in _DOMAIN_RE.finditer(expression):
        next_index = match.end()
        if next_index < len(expression):
            following = expression[next_index]
            category = unicodedata.category(following)
            if following != "_" and category[:1] in {"L", "M", "N"}:
                continue
        domains.append(match.group(1))
    return domains


def _extract_drive_indices(expression: str) -> list[int]:
    out: list[int] = []
    for m in _DRIVE_RE.finditer(expression):
        token = m.group(1) or m.group(2)
        if token is not None:
            out.append(int(token))
    return out


def axis_n_check(
    expression: str, contradiction_count: int = 0
) -> dict[str, Any]:
    """N — Noetic involution imbalance.

    Flags when:

    * the same expression contains both members of an involution pair without
      a ``+`` or ``×`` integrator between them, OR
    * the contradiction history is non-zero (an unresolved opposition is itself
      a structural N flag).
    """
    noetics = _extract_noetic_indices(expression)
    has_integrator = "+" in expression or "×" in expression or "x" in expression
    flagged_pairs: list[tuple[int, int]] = []
    seen = set(noetics)
    for n, partner in NOETIC_INVOLUTION_PAIRS.items():
        if n in seen and partner in seen and not has_integrator:
            pair = tuple(sorted((n, partner)))
            if pair not in flagged_pairs:
                flagged_pairs.append(pair)  # type: ignore[arg-type]

    if contradiction_count > 0:
        return {
            "clean": False,
            "reason": (
                f"contradiction history non-empty ({contradiction_count} entries); "
                "involution opposition unresolved"
            ),
            "noetics": noetics,
            "flagged_pairs": flagged_pairs,
        }
    if flagged_pairs:
        return {
            "clean": False,
            "reason": (
                "expression contains both members of involution pair(s) "
                f"{flagged_pairs} without integrator (+ or ×)"
            ),
            "noetics": noetics,
            "flagged_pairs": flagged_pairs,
        }
    return {
        "clean": True,
        "reason": "no involution imbalance detected",
        "noetics": noetics,
        "flagged_pairs": [],
    }


def axis_w_check(expression: str) -> dict[str, Any]:
    """W — Domain precedence violation.

    The total order is P ≻ C ≻ E ≻ O. We detect violations by scanning
    domains in source order. If the leftmost domain occurrence has lower
    precedence than a strictly later occurrence, flag.
    """
    domains = _extract_domains(expression)
    if len(domains) < 2:
        return {
            "clean": True,
            "reason": "fewer than 2 domain markers; no precedence to violate",
            "domains": domains,
        }
    ranks = [DOMAIN_PRECEDENCE[d] for d in domains]
    # Violation: at any point the running maximum-precedence domain is
    # superseded by a higher-precedence one later in the expression.
    # Concretely, ranks should be non-decreasing for a clean P→C→E→O descent.
    for i in range(1, len(ranks)):
        if ranks[i] < ranks[i - 1]:
            # Lower index = higher precedence; ranks should be non-decreasing.
            return {
                "clean": False,
                "reason": (
                    f"precedence violated: {domains[i - 1]} (rank "
                    f"{ranks[i - 1]}) followed by {domains[i]} (rank "
                    f"{ranks[i]})"
                ),
                "domains": domains,
            }
    return {
        "clean": True,
        "reason": "domain ordering respects P ≻ C ≻ E ≻ O",
        "domains": domains,
    }


def axis_f_check(expression: str) -> dict[str, Any]:
    """F — Drive pair imbalance.

    Flags when the expression contains both members of a drive involution
    pair without an integrator between them.
    """
    drives = _extract_drive_indices(expression)
    has_integrator = "+" in expression or "×" in expression or "x" in expression
    seen = set(drives)
    flagged: list[tuple[int, int]] = []
    for n, partner in DRIVE_INVOLUTION_PAIRS.items():
        if n in seen and partner in seen and not has_integrator:
            pair = tuple(sorted((n, partner)))
            if pair not in flagged:
                flagged.append(pair)  # type: ignore[arg-type]
    if flagged:
        return {
            "clean": False,
            "reason": (
                "expression contains both members of drive involution pair(s) "
                f"{flagged} without integrator"
            ),
            "drives": drives,
            "flagged_pairs": flagged,
        }
    return {
        "clean": True,
        "reason": "no drive imbalance detected",
        "drives": drives,
        "flagged_pairs": [],
    }


def axis_e_check() -> dict[str, Any]:
    """E — State-vector entropy deficit. v1 placeholder."""
    return {
        "clean": True,
        "reason": "placeholder axis — entropy machinery not enabled in v1",
        "placeholder": True,
    }


def axis_s_check() -> dict[str, Any]:
    """S — Sub-Drive cross-domain variance. v1 placeholder."""
    return {
        "clean": True,
        "reason": "placeholder axis — sub-drive variance not enabled in v1",
        "placeholder": True,
    }


def axis_a_check(rpm_satisfied: bool) -> dict[str, Any]:
    """A — Pathway RPM chain violation. Reuses the RPM gate result."""
    if rpm_satisfied:
        return {
            "clean": True,
            "reason": "RPM gate cleared; no pathway chain violation",
        }
    return {
        "clean": False,
        "reason": "RPM gate did not clear; pathway prerequisite chain broken",
    }


def axis_p_check(other_axes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """P — Compound. Flags when more than one of {N, W, F, A} flagged."""
    failing = [
        axis
        for axis, info in other_axes.items()
        if axis in {"N", "W", "F", "A"} and not info.get("clean", True)
    ]
    if len(failing) >= 2:
        return {
            "clean": False,
            "reason": f"compound inversion: axes {failing} all flagged",
            "compound": failing,
        }
    return {
        "clean": True,
        "reason": (
            "no compound inversion (single-axis or fewer flags)"
            if len(failing) == 1
            else "no axes flagged"
        ),
        "compound": failing,
    }


# ---------------------------------------------------------------------------
# Top-level scan
# ---------------------------------------------------------------------------


def run_inversion_scan(
    cas_expression: str,
    history: Iterable[str] | None = None,
    *,
    rpm_satisfied: bool = True,
) -> InversionScanResult:
    """Run all 7 axes and return the aggregated result.

    Parameters
    ----------
    cas_expression:
        The CAS expression to scan.
    history:
        Iterable of past contradiction reasons. Used by axis N. May be ``None``.
    rpm_satisfied:
        Whether the RPM gate cleared on the current belief. Drives axis A.
    """
    contradiction_count = 0 if history is None else sum(1 for _ in history)

    axes: dict[str, dict[str, Any]] = {}
    axes["N"] = axis_n_check(cas_expression, contradiction_count)
    axes["W"] = axis_w_check(cas_expression)
    axes["F"] = axis_f_check(cas_expression)
    axes["E"] = axis_e_check()
    axes["S"] = axis_s_check()
    axes["A"] = axis_a_check(rpm_satisfied)
    axes["P"] = axis_p_check(axes)

    # The scan is "clean" iff every non-placeholder axis is clean.
    clean = all(
        info.get("clean", False)
        for axis, info in axes.items()
        if not info.get("placeholder", False)
    )
    return InversionScanResult(clean=clean, axes=axes)
