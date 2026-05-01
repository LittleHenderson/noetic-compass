"""Level 3 recoverable-record ingestion into IntentIR.

The encoder input remains strictly ``user_prompt``. Target-only fields such as
``cas_expression`` may populate supervised IntentIR labels, but they must never
be concatenated into the natural-language model input.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from cas_native.intent.intent_ir import (
    AxisBinding,
    BuilderTarget,
    EvidenceSpan,
    IntentIR,
    MetaLogicIntent,
    ProductionIngredientIntent,
    ProductionIntent,
    RegisterIntent,
    StateAtom,
)


BUCKET_TO_FAMILY = {
    "v74_baseline": "state",
    "v75_register": "register_state",
    "v76_production": "production",
    "v77_rule_four": "rule_four",
    "v77_omega": "omega",
    "meta_logic": "meta_logic",
}

FAMILY_TO_TRANSITION = {
    "state": "state",
    "register_state": "state",
    "production": "production",
    "rule_four": "relation",
    "omega": "omega_bind",
    "meta_logic": "meta_logic_move",
}

FAMILY_TO_BUILDER = {
    "state": "state_literal_builder",
    "register_state": "register_state_builder",
    "production": "production_recipe_builder",
    "rule_four": "register_copresence_builder",
    "omega": "omega_integration_builder",
    "meta_logic": "meta_logic_symbolic_builder",
}

_STATE_RE = re.compile(
    r"\^(?P<noetic>[0-9])(?![0-9])"
    r"(?:\^(?P<domain>[PCEO]))?"
    r"(?:_\{?(?P<drive>F[1-7])\}?)?"
    r"(?:\|(?P<register>[TAfE]))?"
)
_COEFFICIENT_STATE_RE = re.compile(
    r"(?P<coefficient>[0-9]+(?:\.[0-9]+)?)\*"
    r"(?P<state>\^[0-9](?![0-9])(?:\^[PCEO])?(?:_\{?F[1-7]\}?)?(?:\|[TAfE])?)"
)
_REGISTER_SET_RE = re.compile(r"\|(?:<|\u27e8)([^>\u27e9]+)(?:>|\u27e9)")
_OMEGA_RE = re.compile(r"(?:Omega|[\u03a9]|(?:\u00ce\u00a9))_[A-Za-z0-9_]+")
_PRODUCT_RE = re.compile(r"Product\(([^,]+),\s*([^)]+)\)")


def intent_from_level3_record(record: dict[str, Any]) -> IntentIR:
    """Convert one Level 3 recoverable record into IntentIR."""

    expression = str(record.get("cas_expression", ""))
    bucket = str(record.get("bucket", ""))
    family = BUCKET_TO_FAMILY.get(bucket, _infer_family(expression))
    transition_kind = FAMILY_TO_TRANSITION[family]
    states = tuple(_state_atoms(expression))
    registers = _registers(expression)
    omega_targets = tuple(_omega_targets(expression, str(record.get("user_prompt", ""))))
    production = _production_intent(expression) if family == "production" else None
    meta_logic = _meta_logic_intent(expression) if family == "meta_logic" else None
    axis = AxisBinding(
        noetic=states[0].noetic if states else None,
        domain=states[0].domain if states else None,
        drive=states[0].drive if states else None,
        register=states[0].register if states else None,
        states=states,
    )
    register_intent = RegisterIntent(
        mode=_register_mode(expression, registers, bool(omega_targets)),
        registers=tuple(registers),
        omega_target=omega_targets[0] if _is_integration(expression) and omega_targets else None,
    )
    builder_target = BuilderTarget(
        family=family,
        builder=FAMILY_TO_BUILDER[family],
        canonical_expression=expression or None,
        requires_compiler_validation=True,
        confidence=1.0,
    )

    return IntentIR(
        id=str(record.get("id") or record.get("source_level2_id") or ""),
        source_level2_id=_optional_str(record.get("source_level2_id")),
        user_prompt=str(record.get("user_prompt", "")),
        turn_type="ANSWER",
        expression_family=family,
        transition_kind=transition_kind,
        axis=axis,
        register_intent=register_intent,
        omega_targets=omega_targets,
        production=production,
        meta_logic=meta_logic,
        builder_targets=(builder_target,),
        evidence_spans=(
            EvidenceSpan(
                source_field="user_prompt",
                text=str(record.get("user_prompt", "")),
                role="recoverable_prompt",
            ),
        ),
        authority=_authority_label(expression),
        confidence=1.0,
        cas_expression_target=expression or None,
        tags=tuple(str(tag) for tag in record.get("tags", ()) or ()),
        provenance=dict(record.get("provenance", {}) or {}),
    )


def intents_from_level3_records(records: Iterable[dict[str, Any]]) -> list[IntentIR]:
    return [intent_from_level3_record(record) for record in records]


def load_level3_intents(path: str | Path, limit: int | None = None) -> list[IntentIR]:
    records: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
            if limit is not None and len(records) >= limit:
                break
    return intents_from_level3_records(records)


def _state_atoms(expression: str) -> list[StateAtom]:
    states: list[StateAtom] = []
    seen: set[tuple[int, str | None, str | None, str | None]] = set()
    for match in _STATE_RE.finditer(expression):
        atom = StateAtom(
            noetic=int(match.group("noetic")),
            domain=match.group("domain"),
            drive=match.group("drive"),
            register=match.group("register"),
        )
        key = (atom.noetic, atom.domain, atom.drive, atom.register)
        if key not in seen:
            states.append(atom)
            seen.add(key)
    return states


def _production_intent(expression: str) -> ProductionIntent | None:
    omegas = _omega_targets(expression, "")
    if not omegas:
        return None
    ingredients: list[ProductionIngredientIntent] = []
    for match in _COEFFICIENT_STATE_RE.finditer(expression):
        state = _parse_state(match.group("state"))
        if state is None:
            continue
        ingredients.append(
            ProductionIngredientIntent(
                state=state,
                coefficient=float(match.group("coefficient")),
            )
        )
    if not ingredients:
        return None
    leakage_terms = tuple(part.strip() for part in _leakage_terms(expression))
    return ProductionIntent(
        omega_target=omegas[0],
        ingredients=tuple(ingredients),
        leakage_terms=leakage_terms,
    )


def _parse_state(value: str) -> StateAtom | None:
    match = _STATE_RE.fullmatch(value)
    if match is None:
        return None
    return StateAtom(
        noetic=int(match.group("noetic")),
        domain=match.group("domain"),
        drive=match.group("drive"),
        register=match.group("register"),
    )


def _registers(expression: str) -> list[str]:
    found: list[str] = []
    for state in _state_atoms(expression):
        if state.register is not None:
            found.append(state.register)
    for match in _REGISTER_SET_RE.finditer(expression):
        for item in match.group(1).split(","):
            value = item.strip()
            if value in {"T", "A", "f", "E"}:
                found.append(value)
    return list(dict.fromkeys(found))


def _register_mode(expression: str, registers: list[str], has_omega: bool) -> str:
    if "\u27e8" in expression or "|<" in expression:
        return "set_spec"
    if _is_integration(expression):
        return "integration" if has_omega else "co_presence"
    if " + " in expression and len(registers) > 1:
        return "co_presence"
    if len(registers) == 1:
        return "single"
    if len(registers) > 1:
        return "set_spec"
    return "none"


def _is_integration(expression: str) -> bool:
    return "\u00d7" in expression or "\u00c3\u2014" in expression or re.search(r"\s+x\s+", expression) is not None


def _omega_targets(*texts: str) -> list[str]:
    values: list[str] = []
    for text in texts:
        for match in _OMEGA_RE.finditer(text):
            values.append(_normalize_omega(match.group(0)))
    return list(dict.fromkeys(values))


def _normalize_omega(value: str) -> str:
    suffix = value.split("_", 1)[1] if "_" in value else value
    return f"Omega_{suffix}"


def _leakage_terms(expression: str) -> list[str]:
    terms: list[str] = []
    if "Lambda" not in expression and "\u039b" not in expression and "\u00ce\u203a" not in expression:
        return terms
    for omega in _omega_targets(expression):
        if omega not in terms:
            terms.append(f"Lambda*{omega}")
    return terms[1:] if len(terms) > 1 else []


def _meta_logic_intent(expression: str) -> MetaLogicIntent:
    relations: list[str] = []
    carriers: list[str] = []
    objects: list[str] = []

    product_match = _PRODUCT_RE.search(expression)
    if product_match:
        relations.append("product")
        carriers.extend([product_match.group(1).strip(), product_match.group(2).strip()])

    if any(token in expression for token in ("\u2208", " in ")):
        relations.append("membership")
    if any(token in expression for token in ("\u2282", "\u2286", "subset")):
        relations.append("subset")
    if "CoverOf(" in expression:
        relations.append("cover")
    if "PartitionOf(" in expression:
        relations.append("partition")
    if "Pullback(" in expression:
        relations.append("pullback")
    if "TraceSet" in expression:
        relations.append("trace_nesting")
    if "EvidenceSet" in expression or "ValidatedClaimSet" in expression:
        relations.append("evidence")
    if "InstructionSet" in expression or "UserRequestSet" in expression:
        relations.append("authority")

    for token in re.findall(r"[A-Za-z][A-Za-z0-9_]*(?:Cluster|Set)?(?:\{[^}]*\})?", expression):
        if token not in {"Product", "CoverOf", "PartitionOf", "Pullback"}:
            objects.append(token)

    return MetaLogicIntent(
        relations=tuple(dict.fromkeys(relations)),
        carriers=tuple(dict.fromkeys(carriers)),
        objects=tuple(dict.fromkeys(objects)),
    )


def _infer_family(expression: str) -> str:
    if "Theta(" in expression or "\u0398(" in expression or "\u00ce\u02dc(" in expression:
        return "production"
    if _OMEGA_RE.search(expression):
        return "omega"
    if any(token in expression for token in ("Cluster{", "Set{", "Product(", "Pullback(", "CoverOf(", "PartitionOf(")):
        return "meta_logic"
    if _registers(expression):
        return "register_state"
    return "state"


def _authority_label(expression: str) -> str:
    if "UserRequestSet" in expression and "SystemInstructionSet" in expression:
        return "blocked"
    if "InstructionSet" in expression or "UserRequestSet" in expression:
        return "admitted"
    return "none"


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
