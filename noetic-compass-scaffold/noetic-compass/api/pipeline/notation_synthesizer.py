"""Real-time CAS notation synthesizer.

Derives a CAS expression from actual pipeline computation results, then
validates it through the compiler.  The notation is a formal description
of what the system *found*, not a prediction of what it expected to find.

Inputs consumed (all produced by earlier pipeline stages):
  - operator_scores       10 floats in [0, 1]
  - raw_scores_0_to_10    10 floats in [0, 10]
  - domain_averages       4  floats  [P, C, E, O]
  - drive_chains          7  lists of [D, W, P] floats
  - a0_score              float
  - rpm_completeness      float
  - inversion_axis_scores 7  floats in [0, 1]
  - inversion_evidence    list of per-axis evidence dicts
  - fractal_sequence      list of ints (dominant operator sequence)
  - fractal_classification str

Output: a ``SynthesizedNotation`` containing the source expression, the
compiler artifact, and provenance metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from api.notation.compiler import (
    compile_expression,
    CompilationArtifact,
    OPERATOR_NAMES,
    DOMAIN_NAMES,
    DRIVE_NAMES,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DOMAIN_CODES = ("P", "C", "E", "O")
DRIVE_COUNT = 7

# An operator must score above this (on the 0-10 scale) to be "significant"
OPERATOR_SIGNIFICANCE_THRESHOLD = 5.0

# A domain average must be above this (normalised 0-1) to qualify
DOMAIN_SIGNIFICANCE_THRESHOLD = 0.45

# A drive chain stage must be above this to count as "satisfied"
DRIVE_CHAIN_STAGE_THRESHOLD = 0.5

# An inversion axis must score *below* this to be flagged (low = vulnerable)
INVERSION_FLAG_THRESHOLD = 0.5

# Maximum operators to include so the expression stays readable
MAX_OPERATORS = 4

# Maximum drives to include
MAX_DRIVES = 3

INVERSION_AXIS_NAMES = ("N", "W", "F", "E", "S", "A", "P")
REGISTER_CODES = ("T", "A", "f", "E")

REGISTER_SIGNAL_PATTERNS = {
    "T": (
        "transcendent", "meaning", "purpose", "vision", "calling", "ultimate",
        "sacred", "spiritual", "beyond", "integrative", "higher order",
    ),
    "A": (
        "analytic", "analytical", "analysis", "logic", "logical", "reason",
        "rational", "evidence", "deduce", "infer", "step by step", "explicit",
    ),
    "f": (
        "affective", "emotion", "emotional", "feeling", "feel", "felt",
        "value-laden", "visceral", "heart", "care", "love", "fear", "empathy",
    ),
    "E": (
        "embodied", "body", "bodily", "somatic", "sensorimotor", "physical",
        "concrete", "kinesthetic", "hands-on", "breath", "gut", "material",
    ),
}

PRODUCTION_SIGNAL_PATTERNS = (
    "produce", "production", "generate", "create", "build", "make",
    "synthesize", "recipe", "yield", "output", "result", "turn into",
    "convert", "from inputs", "ingredients",
)

CATALYST_SIGNAL_PATTERNS = (
    "catalyst", "catalyze", "enable", "accelerate", "support", "scaffold",
    "deadline", "context", "resource", "mentor", "feedback",
)

INHIBITOR_SIGNAL_PATTERNS = (
    "inhibitor", "inhibit", "block", "constraint", "fatigue", "noise",
    "friction", "risk", "obstacle", "delay", "resistance", "interference",
)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class SynthesizedNotation:
    """The compiler-validated CAS expression derived from pipeline results."""
    source: str
    valid: bool
    english: str
    compiler_artifact: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Core synthesis logic
# ---------------------------------------------------------------------------

def _pick_significant_operators(
    raw_scores: list[float],
) -> list[int]:
    """Return indices of the most significant operators, ordered by score."""
    scored = [
        (idx, score)
        for idx, score in enumerate(raw_scores)
        if score >= OPERATOR_SIGNIFICANCE_THRESHOLD
    ]
    scored.sort(key=lambda pair: -pair[1])
    return [idx for idx, _ in scored[:MAX_OPERATORS]]


def _pick_significant_domains(
    domain_averages: list[float],
    *,
    need_fallback: bool = False,
) -> list[str]:
    """Return domain codes for domains above the significance threshold.

    When need_fallback is True and no domain passes threshold, returns the
    strongest domain so notation always has proper CO-N^D form.
    """
    result = [
        DOMAIN_CODES[idx]
        for idx, avg in enumerate(domain_averages)
        if avg >= DOMAIN_SIGNIFICANCE_THRESHOLD and idx < len(DOMAIN_CODES)
    ]
    if not result and need_fallback:
        best_idx = max(range(len(domain_averages)), key=lambda i: domain_averages[i])
        if domain_averages[best_idx] > 0:
            result = [DOMAIN_CODES[best_idx]]
    return result


def _pick_significant_drives(
    drive_chains: list[list[float]],
    a0_score: float,
) -> tuple[list[int], list[int]]:
    """Return (rpm_drives, plain_drives).

    rpm_drives: drives whose full D->W->P chain is intact (all stages pass).
    plain_drives: drives that are active but have a broken chain.
    """
    rpm_drives: list[int] = []
    plain_drives: list[int] = []

    for drive_idx, chain in enumerate(drive_chains):
        if drive_idx >= DRIVE_COUNT:
            break

        # A chain is "intact" if A0 + all three stages pass
        chain_intact = a0_score >= DRIVE_CHAIN_STAGE_THRESHOLD and all(
            stage >= DRIVE_CHAIN_STAGE_THRESHOLD for stage in chain
        )
        # A drive is "active" if at least the first stage (Dormant/D) passes
        first_stage_active = len(chain) > 0 and chain[0] >= DRIVE_CHAIN_STAGE_THRESHOLD

        if chain_intact:
            rpm_drives.append(drive_idx)
        elif first_stage_active:
            plain_drives.append(drive_idx)

    # Cap total drives to keep expression readable
    rpm_drives = rpm_drives[:MAX_DRIVES]
    remaining_slots = MAX_DRIVES - len(rpm_drives)
    plain_drives = plain_drives[:remaining_slots]

    return rpm_drives, plain_drives


def _pick_flagged_inversions(axis_scores: list[float]) -> list[str]:
    """Return axis names for inversions that were detected (low resistance)."""
    flagged = []
    for idx, score in enumerate(axis_scores):
        if idx < len(INVERSION_AXIS_NAMES) and score < INVERSION_FLAG_THRESHOLD:
            flagged.append(INVERSION_AXIS_NAMES[idx])
    return flagged


def _text_has_any(text_lower: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern in text_lower for pattern in patterns)


def _infer_registers(source_text: str | None) -> list[str]:
    """Return register codes strongly signaled by source text, in CAS order."""
    if not source_text:
        return []
    text_lower = source_text.lower()
    return [
        register
        for register in REGISTER_CODES
        if _text_has_any(text_lower, REGISTER_SIGNAL_PATTERNS[register])
    ]


def _select_register_for_domain(domain: str, registers: list[str]) -> str | None:
    """Pick the most natural register for a domain from detected registers."""
    if not registers:
        return None
    preferred = {
        "P": "T",
        "C": "A",
        "E": "f",
        "O": "E",
    }.get(domain)
    if preferred in registers:
        return preferred
    return registers[0]


def _sanitize_omega_name(source_text: str | None, registers: list[str]) -> str:
    """Build a stable v7.6 production target name from text signals."""
    if not source_text:
        return "synthesis"
    text_lower = source_text.lower()
    if "insight" in text_lower or "understand" in text_lower:
        return "insight"
    if "decision" in text_lower or "decide" in text_lower:
        return "decision"
    if "plan" in text_lower or "workflow" in text_lower:
        return "plan"
    if "refusal" in text_lower or "boundary" in text_lower:
        return "refusal"
    if {"A", "f", "T"}.issubset(set(registers)):
        return "integrated_judgment"
    return "synthesis"


def _condition_name(source_text: str | None, patterns: tuple[str, ...], default: str) -> str | None:
    if not source_text:
        return None
    text_lower = source_text.lower()
    if not _text_has_any(text_lower, patterns):
        return None
    names = (
        ("deadline", "context", "mentor", "feedback")
        if default == "context"
        else ("fatigue", "noise", "risk", "constraint")
    )
    for name in names:
        if name in text_lower:
            return name
    return default


_INVOLUTION_PAIRS = {(2, 3), (3, 2), (5, 6), (6, 5), (8, 9), (9, 8)}
_OP_INVOLUTION_MAP = {2: 3, 3: 2, 5: 6, 6: 5, 8: 9, 9: 8}


def _drive_ranking(drive_chains: list[list[float]]) -> list[int]:
    """Return drive indices sorted by first-stage activation (strongest first).
    Always returns at least one drive (F4 Connection as default)."""
    if not drive_chains:
        return [3]  # F4 Connection as default
    indexed = [(i, chain[0] if chain else 0.0) for i, chain in enumerate(drive_chains)]
    indexed.sort(key=lambda x: -x[1])
    result = [i for i, v in indexed if v > 0.05]
    return result if result else [3]  # F4 fallback


def _state_with_drive(
    op: int,
    dom: str,
    drive_rank: list[int],
    op_index_in_group: int,
    register: str | None = None,
) -> str:
    """Build a state expression like CO-3^P_{F2}.

    Cycles through ranked drives so each operator gets a different one.
    RPM wrapping is handled at the group level, not per-operand,
    because × only accepts state operands (not RPM results).
    """
    if drive_rank:
        drv = drive_rank[op_index_in_group % len(drive_rank)]
        state = f"CO-{op}^{dom}_{{F{drv + 1}}}"
    else:
        state = f"CO-{op}^{dom}"
    return f"{state}|{register}" if register else state


def _state_with_register_set(
    op: int,
    dom: str,
    drive_rank: list[int],
    registers: list[str],
) -> str:
    state = _state_with_drive(op, dom, drive_rank, 0)
    return f"{state}|<{','.join(registers)}>"


def _build_expression(
    operators: list[int],
    domains: list[str],
    rpm_drives: list[int],
    plain_drives: list[int],
    fractal_sequence: list[int] | None,
    fractal_classification: str | None,
    flagged_inversions: list[str] | None = None,
    drive_chains: list[list[float]] | None = None,
    raw_scores: list[float] | None = None,
    source_text: str | None = None,
) -> str:
    """Assemble a rich, varied CAS expression using all 5 generative operations.

    Every operator gets a drive subscript. RPM wraps states with complete
    prerequisite chains. Fractal sequences are always generated when 3+
    operators are present. Parenthetical grouping shows PEMDAS structure.
    Different signal patterns produce structurally different expressions.
    """
    if not operators:
        parts: list[str] = []
        for d in rpm_drives:
            parts.append(f"RPM(F{d + 1})")
        for d in plain_drives:
            parts.append(f"F{d + 1}")
        return " + ".join(parts) if parts else ""

    chains = drive_chains or []
    scores = raw_scores or [5.0] * 10
    flagged = flagged_inversions or []
    drive_rank = _drive_ranking(chains)
    registers = _infer_registers(source_text)
    register_set = [reg for reg in ("A", "f", "T") if reg in registers]

    # --- 1. Separate involution pairs for ÷ ---
    division_parts: list[str] = []
    used_in_div: set[int] = set()
    for i, a in enumerate(operators):
        if a in used_in_div:
            continue
        for b in operators[i + 1:]:
            if b in used_in_div:
                continue
            if (a, b) in _INVOLUTION_PAIRS:
                dom = domains[0] if domains else "P"
                reg = _select_register_for_domain(dom, registers)
                la = _state_with_drive(a, dom, drive_rank, 0, reg)
                lb = _state_with_drive(b, dom, drive_rank, 1, reg)
                division_parts.append(f"({la} / {lb})")
                used_in_div.add(a)
                used_in_div.add(b)
                break

    remaining = [op for op in operators if op not in used_in_div]

    # --- 2. Build per-domain state expressions with drives ---
    # For the → chain: use top 2 operators per domain (keeps → valid).
    # Extra operators go to a co-present + statement.
    ARROW_MAX_OPS = 2  # → requires singular result from each side
    domain_groups: dict[str, list[str]] = {}
    extra_ops: dict[str, list[str]] = {}
    for dom in domains:
        states = []
        overflow = []
        for idx, op in enumerate(remaining):
            s = _state_with_drive(
                op,
                dom,
                drive_rank,
                idx,
                _select_register_for_domain(dom, registers),
            )
            if len(states) < ARROW_MAX_OPS:
                states.append(s)
            else:
                overflow.append(s)
        if states:
            domain_groups[dom] = states
        if overflow:
            extra_ops[dom] = overflow

    # --- 3. Build per-domain expressions with × ---
    domain_exprs: list[str] = []
    dom_order = [d for d in ("P", "C", "E", "O") if d in domain_groups]
    for dom in dom_order:
        states = domain_groups[dom]
        if len(states) == 1:
            domain_exprs.append(states[0])
        else:
            domain_exprs.append(f"({states[0]} * {states[1]})")

    # Build RPM wrapping as a separate statement for the lead operator
    # (→ doesn't accept RPM on either side, so RPM is its own statement)
    rpm_stmt = None
    if rpm_drives and remaining and dom_order:
        lead_op = remaining[0]
        lead_dom = dom_order[0]
        lead_state = _state_with_drive(
            lead_op,
            lead_dom,
            drive_rank,
            0,
            _select_register_for_domain(lead_dom, registers),
        )
        rpm_stmt = f"RPM({lead_state})"

    # --- 4. Connect top 2 domains with → (descent) ---
    if len(domain_exprs) >= 2:
        main_expr = f"{domain_exprs[0]} -> {domain_exprs[1]}"
    elif domain_exprs:
        main_expr = domain_exprs[0]
    else:
        main_expr = ""

    # --- 5. Build - (subtraction) expressions for inversions ---
    minus_parts: list[str] = []
    inversion_map = {
        "N": (0, "P"), "W": (1, "C"), "F": (4, "E"),
        "E": (7, "E"), "S": (2, "O"), "A": (8, "O"), "P": (5, "P"),
    }
    for axis in flagged[:2]:  # Cap at 2 to keep expression readable
        inv = inversion_map.get(axis)
        if inv:
            idx, dom = inv
            partner = _OP_INVOLUTION_MAP.get(idx, (idx + 5) % 10)
            reg = _select_register_for_domain(dom, registers)
            la = _state_with_drive(idx, dom, drive_rank, 0, reg)
            lb = _state_with_drive(partner, dom, drive_rank, 1, reg)
            minus_parts.append(f"({la} - {lb})")

    # --- 6. Build fractal Φ⟨...⟩ from operator activation order ---
    fractal_part = None
    if fractal_sequence and len(fractal_sequence) >= 2 and fractal_classification not in (None, "neutral"):
        seq_str = ":".join(str(op) for op in fractal_sequence)
        fractal_part = f"Phi<{seq_str}>"
    elif len(operators) >= 3:
        # Auto-generate fractal from operator order (strongest to weakest)
        ordered = sorted(operators, key=lambda o: -scores[o] if o < len(scores) else 0)
        seq_str = ":".join(str(op) for op in ordered)
        fractal_part = f"Phi<{seq_str}>"

    # --- 7. Assemble the full program ---
    statements: list[str] = []

    # Main expression (× within domain, → across domains)
    if main_expr:
        statements.append(main_expr)

    # RPM wrapping on the lead state (separate statement)
    if rpm_stmt:
        statements.append(rpm_stmt)

    # ÷ division pairs
    for dp in division_parts:
        statements.append(dp)

    # - subtraction inversions
    for mp in minus_parts:
        statements.append(mp)

    # + co-present: overflow from primary domain + drives (cap at 4 items)
    coexist: list[str] = []
    # Overflow operators from first domain only (keeps it readable)
    if dom_order and dom_order[0] in extra_ops:
        coexist.extend(extra_ops[dom_order[0]][:2])
    # Extra domain expressions (3rd, 4th domain) — just one each
    for expr in domain_exprs[2:4]:
        coexist.append(expr)
    # Drives
    for d in rpm_drives[:2]:
        coexist.append(f"RPM(F{d + 1})")
    for d in plain_drives[:2]:
        coexist.append(f"F{d + 1}")
    if coexist:
        statements.append(" + ".join(coexist))

    # ∘ / Φ fractal
    if fractal_part:
        statements.append(fractal_part)

    # v7.7: same-state multi-register signals must use co-presence (`+`) or
    # register-set specification, not generative multiplication.
    if len(register_set) >= 3 and remaining:
        dom = dom_order[0] if dom_order else (domains[0] if domains else "P")
        op = remaining[0]
        statements.append(
            " + ".join(
                _state_with_drive(op, dom, drive_rank, 0, reg)
                for reg in register_set
            )
        )
        statements.append(_state_with_register_set(op, dom, drive_rank, register_set))

    # v7.6: emit production recipes only for strong production-language text.
    text_lower = source_text.lower() if source_text else ""
    if source_text and _text_has_any(text_lower, PRODUCTION_SIGNAL_PATTERNS) and remaining:
        target = _sanitize_omega_name(source_text, registers)
        condition_parts: list[str] = []
        catalyst = _condition_name(source_text, CATALYST_SIGNAL_PATTERNS, "context")
        inhibitor = _condition_name(source_text, INHIBITOR_SIGNAL_PATTERNS, "constraint")
        if catalyst:
            condition_parts.append(f"kappa_{catalyst}")
        if inhibitor:
            condition_parts.append(f"iota_{inhibitor}")
        condition_clause = f" | {', '.join(condition_parts)}" if condition_parts else ""
        recipe_dom = dom_order[0] if dom_order else (domains[0] if domains else "P")
        recipe_states = []
        for idx, op in enumerate(remaining[:3]):
            reg = registers[idx % len(registers)] if registers else None
            recipe_states.append(_state_with_drive(op, recipe_dom, drive_rank, idx, reg))
        terms = " + ".join(f"1*{state}" for state in recipe_states)
        statements.append(
            f"Theta(Omega_{target}){condition_clause} = {terms} -> Omega_{target}"
        )

    return "; ".join(statements)


def synthesize_notation(
    *,
    operator_scores: list[float],
    raw_scores_0_to_10: list[float],
    domain_averages: list[float],
    drive_chains: list[list[float]],
    a0_score: float,
    rpm_completeness: float,
    inversion_axis_scores: list[float],
    fractal_sequence: list[int] | None = None,
    fractal_classification: str | None = None,
    source_text: str | None = None,
) -> SynthesizedNotation:
    """Synthesize a CAS notation expression from real pipeline results.

    This is the core function: it reads what the pipeline actually computed
    and produces a compiler-validated formal expression.
    """
    # Extract significant components from the scores
    operators = _pick_significant_operators(raw_scores_0_to_10)
    domains = _pick_significant_domains(
        domain_averages,
        need_fallback=len(operators) > 0,
    )
    rpm_drives, plain_drives = _pick_significant_drives(drive_chains, a0_score)
    flagged_inversions = _pick_flagged_inversions(inversion_axis_scores)

    # Build a rich expression using all 5 generative operations
    source = _build_expression(
        operators=operators,
        domains=domains,
        rpm_drives=rpm_drives,
        plain_drives=plain_drives,
        fractal_sequence=fractal_sequence,
        fractal_classification=fractal_classification,
        flagged_inversions=flagged_inversions,
        drive_chains=drive_chains,
        raw_scores=raw_scores_0_to_10,
        source_text=source_text,
    )

    if not source.strip():
        return SynthesizedNotation(
            source="",
            valid=False,
            english="No significant cognitive patterns detected",
            provenance={
                "operators_found": 0,
                "domains_found": 0,
                "drives_found": 0,
                "reason": "all scores below significance thresholds",
            },
        )

    # Compile through the real compiler
    artifact: CompilationArtifact = compile_expression(source)
    registers = _infer_registers(source_text)

    # If compiler rejects it, try progressively simpler fallbacks
    if not artifact.valid and operators:
        # Fallback 1: operators with best domain, joined by multiplication
        if domains:
            best_dom = domains[0]
            fallback = " * ".join(f"CO-{op}^{best_dom}" for op in operators)
            artifact = compile_expression(fallback)
            if artifact.valid:
                source = fallback
        # Fallback 2: operators with best domain, space-separated
        if not artifact.valid and domains:
            best_dom = domains[0]
            fallback = " ".join(f"CO-{op}^{best_dom}" for op in operators)
            artifact = compile_expression(fallback)
            if artifact.valid:
                source = fallback
        # Fallback 3: bare operators (last resort)
        if not artifact.valid:
            fallback = " ".join(f"CO-{op}" for op in operators)
            artifact = compile_expression(fallback)
            if artifact.valid:
                source = fallback

    # Build English directly from the extracted components (the parser
    # chokes on semicolons that the compiler handles fine, so we render
    # English ourselves from the semantic components we already have).
    english = _render_english(operators, domains, rpm_drives, plain_drives, fractal_classification)

    provenance = {
        "operators_found": len(operators),
        "operators": [f"CO-{op}" for op in operators],
        "domains_found": len(domains),
        "domains": domains,
        "rpm_drives": [f"F{d + 1}" for d in rpm_drives],
        "plain_drives": [f"F{d + 1}" for d in plain_drives],
        "flagged_inversions": flagged_inversions,
        "registers": registers,
        "production_recipe": "Theta(Omega_" in source,
        "register_copresence": "|<" in source or any(f"|{reg}" in source for reg in registers),
        "fractal_classification": fractal_classification,
        "rpm_completeness": round(rpm_completeness, 4),
        "compiler_engine": artifact.engine,
        "compiler_valid": artifact.valid,
        "compiler_error": artifact.error,
    }

    return SynthesizedNotation(
        source=source,
        valid=artifact.valid,
        english=english,
        compiler_artifact=artifact.to_dict() if artifact.valid else {},
        provenance=provenance,
    )


def _render_english(
    operators: list[int],
    domains: list[str],
    rpm_drives: list[int],
    plain_drives: list[int],
    fractal_classification: str | None,
) -> str:
    """Build a plain-English description from the semantic components."""
    parts: list[str] = []

    if operators:
        op_labels = []
        for op in operators:
            name = OPERATOR_NAMES[op] if op < len(OPERATOR_NAMES) else f"CO-{op}"
            op_labels.append(f"CO-{op} ({name})")
        parts.append(" and ".join(op_labels))

    if domains:
        dom_labels = [f"{DOMAIN_NAMES.get(d, d)}" for d in domains]
        parts.append("in the " + " and ".join(dom_labels) + (" Domains" if len(dom_labels) > 1 else " Domain"))

    drive_labels: list[str] = []
    for d in rpm_drives:
        name = DRIVE_NAMES.get(d + 1, f"F{d + 1}")
        drive_labels.append(f"F{d + 1} ({name}, RPM chain intact)")
    for d in plain_drives:
        name = DRIVE_NAMES.get(d + 1, f"F{d + 1}")
        drive_labels.append(f"F{d + 1} ({name})")
    if drive_labels:
        parts.append("grounded in " + ", ".join(drive_labels))

    if fractal_classification and fractal_classification != "neutral":
        parts.append(f"with {fractal_classification} fractal dynamics")

    return " ".join(parts) if parts else "No significant cognitive patterns detected"
