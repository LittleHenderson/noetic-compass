"""Deterministic expression builders for IntentIR.

These builders are intentionally conservative. They produce candidate CAS
strings from typed intent, then downstream compiler validation decides whether
the candidate is admissible.
"""

from __future__ import annotations

from cas_native.intent.intent_ir import IntentIR, ProductionIntent


def build_candidate_expressions(intent: IntentIR) -> list[str]:
    """Build ordered candidate CAS expressions for an intent."""

    candidates: list[str] = []
    for target in intent.builder_targets:
        if target.canonical_expression:
            candidates.append(target.canonical_expression)

    if intent.expression_family in {"state", "register_state"}:
        for state in intent.axis.states:
            candidates.append(state.to_cas())

    if intent.expression_family == "production" and intent.production is not None:
        candidates.append(_build_production_expression(intent.production))

    return _dedupe(candidates)


def _build_production_expression(production: ProductionIntent) -> str:
    parts = [
        f"{_format_number(ingredient.coefficient)}*{ingredient.state.to_cas()}"
        for ingredient in production.ingredients
    ]
    parts.extend(production.leakage_terms)
    return f"Theta({production.omega_target}) = {' + '.join(parts)} -> {production.omega_target}"


def _format_number(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.6g}"


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
