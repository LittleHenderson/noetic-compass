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

import re
from dataclasses import dataclass, field
from typing import Any, Optional

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


# ---------------------------------------------------------------------------
# Meta-logic trigger vocabulary (CAS v7.8 set/membership/subset assertions)
# ---------------------------------------------------------------------------
#
# Conservative discipline: emit typed meta-logic assertions ONLY when the
# source text uses explicit set-reference language AND we can resolve the
# operands to compiler-admitted carriers. False-fire cost > miss cost. When
# in doubt, return None and let the existing v7.4-v7.7 emission paths run.
#
# Compiler-admitted forms (validated against api/notation/compiler.py):
#   ^N ∈ Noetics                         CO-N ∈ Noetics
#   ^N^D ∈ States                        Cn / Pn ∈ States
#   NoeticCluster{^a, ^b} ⊆ Noetics      StateCluster{^a^P, ^b^O} ⊆ States
#   NoeticCluster{...} ∩ NoeticCluster{...}    same-carrier ∪/∩/∖ only
#   Noetics ∖ NoeticCluster{^4}          named-meta minus matching cluster

_CANONICAL_META_SETS: dict[str, str] = {
    "noetics": "Noetics",
    "domains": "Domains",
    "worlds": "Domains",
    "drives": "Drives",
    "registers": "Registers",
    "states": "States",
    "foundations": "Foundations",
    "subfoundations": "SubFoundations",
}

# Words that, when adjacent to "union" / "intersection" / "contains" / "is in",
# definitively indicate everyday senses, NOT set-theoretic ones.
_UNION_NEGATIVE_CONTEXTS = (
    "labor union", "trade union", "credit union", "european union",
    "soviet union", "civil union", "students union", "student union",
    "union jack", "union square", "union member", "union dues",
    "union of soviet",
)
_INTERSECTION_NEGATIVE_CONTEXTS = (
    "street intersection", "intersection of his", "intersection of her",
    "intersection of their", "intersection of my", "intersection of our",
    "busy intersection", "traffic intersection", "intersection of life",
    "intersection of lives", "intersection of identity",
    "intersection of identities", "at the intersection",
)
_DIFFERENCE_NEGATIVE_CONTEXTS = (
    "difference between us", "difference between them", "difference between you",
    "the difference is", "made a difference", "make a difference",
    "no difference", "all the difference", "world of difference",
)
_CONTAINS_NEGATIVE_CONTEXTS = (
    "contains nuts", "contains gluten", "contains alcohol", "contains caffeine",
    "contains sugar", "contains traces", "contains lead", "contains asbestos",
    "this contains", "package contains", "bottle contains", "box contains",
)
_IS_IN_NEGATIVE_CONTEXTS = (
    "is in trouble", "is in love", "is in danger", "is in pain",
    "is in charge", "is in town", "is in stock", "is in line",
    "is in shape", "is in tune", "is in fact", "is in front",
    "is in back", "is in there", "is in here", "is in question",
    "is in doubt", "is in error", "is in luck", "is in ruins",
)


# Regex for individual Noetic operator references in prose.
_NOETIC_REF = re.compile(r"\^(\d)\b|CO-(\d)\b")
# Regex for a domain-qualified state, e.g. ^2^P or CO-3^E or shorthand C7
_STATE_REF = re.compile(r"\^(\d)\^([PCEO])\b|CO-(\d)\^([PCEO])\b|\b([PCEO])(\d)\b")
_NUMBER_WORDS = {
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
}


def _normalize_numeric_meta_refs(text: str) -> str:
    """Normalize common spoken/written carrier refs to compiler tokens.

    Examples:
      "Foundations 1 and 7" -> "Foundation_1 and Foundation_7"
      "Drives two and three" -> "F2 and F3"

    This intentionally covers only CAS carrier nouns whose numeric members are
    unambiguous. Vague prose still falls through to the baseline synthesizer.
    """
    if not text:
        return text

    number = r"(?:[0-9]|zero|one|two|three|four|five|six|seven|eight|nine)"
    number_list = rf"{number}(?:\s*(?:,|and)\s*{number})*"
    carrier_specs = (
        (re.compile(rf"\bfoundations?\s+({number_list})\b", re.IGNORECASE), "Foundation_"),
        (re.compile(rf"\bdrives?\s+({number_list})\b", re.IGNORECASE), "F"),
        (re.compile(rf"\bnoetics?\s+({number_list})\b", re.IGNORECASE), "^"),
    )

    def normalize_number(raw: str) -> str:
        return _NUMBER_WORDS.get(raw.lower(), raw)

    def split_numbers(raw: str) -> list[str]:
        return [
            normalize_number(part)
            for part in re.findall(number, raw, flags=re.IGNORECASE)
        ]

    normalized = text
    for pattern, prefix in carrier_specs:
        def replace(match: re.Match[str]) -> str:
            values = split_numbers(match.group(1))
            if not values:
                return match.group(0)
            return " and ".join(f"{prefix}{value}" for value in values)

        normalized = pattern.sub(replace, normalized)
    return normalized


def _detect_set_operation_vocabulary(text: str) -> Optional[str]:
    """Detect explicit set-operation vocabulary.

    Returns 'Union', 'Intersection', 'Difference', or None.

    Conservative: requires the prose to be explicitly framing a set
    operation. Common everyday senses ("labor union", "street intersection",
    "the difference between us") are filtered out before firing.
    """
    if not text:
        return None
    lower = text.lower()

    # Difference triggers (check first since "everything in X except Y" is
    # the most explicit set-difference phrase and shouldn't be shadowed).
    diff_patterns = (
        "everything in ", "all of ", "all that are in ", "all things in ",
    )
    has_except_pattern = (
        any(p in lower for p in diff_patterns) and
        (" except " in lower or " excluding " in lower or " but not " in lower)
    )
    has_aint_pattern = (
        " that aren't " in lower or " that are not " in lower or
        " that isn't " in lower or " that is not " in lower
    ) and any(p in lower for p in diff_patterns)
    has_minus_pattern = bool(
        re.search(
            r"\b(noetics|domains|states|drives|registers|foundations|subfoundations)"
            r"\s+(?:minus|excluding)\s+",
            lower,
        )
    )
    if (has_except_pattern or has_aint_pattern or has_minus_pattern) and not any(
        ctx in lower for ctx in _DIFFERENCE_NEGATIVE_CONTEXTS
    ):
        return "Difference"

    # Union triggers
    union_phrases = (
        "union of ", "combined set of ", "all of ",
    )
    union_together_phrases = (
        "all of ", "both of ",
    )
    has_union_phrase = any(p in lower for p in union_phrases) and " and " in lower
    has_together_phrase = (
        any(p in lower for p in union_together_phrases)
        and " together" in lower
        and " and " in lower
    )
    if (has_union_phrase or has_together_phrase) and not any(
        ctx in lower for ctx in _UNION_NEGATIVE_CONTEXTS
    ):
        # Require an actual "union of" or "combined set of" or "together"
        # construction — NOT a bare "all of <one thing>".
        if "union of " in lower or "combined set of " in lower or " together" in lower:
            return "Union"

    # Intersection triggers
    intersection_phrases = (
        "intersection of ", "common to both ", "overlap of ", "what ",
    )
    has_intersection_of = "intersection of " in lower
    has_common_to_both = "common to both " in lower
    has_overlap_of = "overlap of " in lower
    has_what_share = bool(re.search(r"\bwhat\b.+?\band\b.+?\bshare\b", lower))
    if (
        (has_intersection_of or has_common_to_both or has_overlap_of or has_what_share)
        and not any(ctx in lower for ctx in _INTERSECTION_NEGATIVE_CONTEXTS)
    ):
        return "Intersection"

    return None


def _detect_membership_vocabulary(text: str) -> Optional[str]:
    """Detect membership / non-membership trigger vocabulary.

    Returns 'Member', 'NotMember', or None. Requires pairing with a
    recognized meta-set name; bare "is in" without a meta-set falls through.
    """
    if not text:
        return None
    lower = text.lower()

    # Build meta-set alternation for trigger phrasing
    set_alt = "|".join(_CANONICAL_META_SETS.keys())

    not_member_patterns = (
        rf"\bis\s+not\s+a\s+member\s+of\s+({set_alt})\b",
        rf"\bisn't\s+a\s+member\s+of\s+({set_alt})\b",
        rf"\bdoes\s+not\s+belong\s+to\s+({set_alt})\b",
        rf"\bdoesn't\s+belong\s+to\s+({set_alt})\b",
        rf"\bis\s+not\s+in\s+({set_alt})\b",
        rf"\bisn't\s+in\s+({set_alt})\b",
    )
    for pat in not_member_patterns:
        if re.search(pat, lower):
            return "NotMember"

    member_patterns = (
        rf"\bis\s+a\s+member\s+of\s+({set_alt})\b",
        rf"\bbelongs\s+to\s+({set_alt})\b",
        rf"\bis\s+in\s+({set_alt})\b",
    )
    for pat in member_patterns:
        if re.search(pat, lower):
            # Defensive: require meta-set is the actual NEXT noun, so we
            # don't mis-fire on "is in trouble" etc.
            if not any(neg in lower for neg in _IS_IN_NEGATIVE_CONTEXTS):
                return "Member"

    return None


def _detect_subset_vocabulary(text: str) -> Optional[str]:
    """Detect subset / superset trigger vocabulary.

    Returns 'Subset', 'SubsetEq', 'Superset', 'SupersetEq', or None.
    Requires pairing with a recognized meta-set carrier.
    """
    if not text:
        return None
    lower = text.lower()
    set_alt = "|".join(_CANONICAL_META_SETS.keys())

    # Order matters — check ⊆/⊇ before bare ⊂/⊃ so "is at most" wins over
    # plain "is a subset of".
    subseteq_patterns = (
        rf"\bis\s+a\s+subset\s+of\s+or\s+equals?\s+({set_alt})\b",
        rf"\bis\s+at\s+most\s+({set_alt})\b",
    )
    for pat in subseteq_patterns:
        if re.search(pat, lower):
            return "SubsetEq"

    supseteq_patterns = (
        rf"\b({set_alt})\s+contains\s+or\s+equals?\s+",
        rf"\bis\s+at\s+least\s+({set_alt})\b",
    )
    for pat in supseteq_patterns:
        if re.search(pat, lower):
            return "SupersetEq"

    subset_patterns = (
        rf"\bis\s+contained\s+in\s+({set_alt})\b",
        rf"\bis\s+a\s+subset\s+of\s+({set_alt})\b",
        rf"\bis\s+part\s+of\s+({set_alt})\b",
    )
    for pat in subset_patterns:
        if re.search(pat, lower):
            return "Subset"

    superset_patterns = (
        rf"\b({set_alt})\s+contains\s+",
        rf"\b({set_alt})\s+includes\s+",
    )
    for pat in superset_patterns:
        if re.search(pat, lower):
            if not any(neg in lower for neg in _CONTAINS_NEGATIVE_CONTEXTS):
                return "Superset"

    return None


def _resolve_meta_set_operand(text_fragment: str) -> Optional[str]:
    """Resolve a text fragment to a canonical meta-set name OR cluster.

    Priority:
      1. If the fragment is a bare canonical meta-set name → return it
         capitalized ("Noetics", "Domains", "States", ...).
      2. If the fragment is a single bare Domain code (P/C/E/O) →
         return it (singular Domain element for membership).
      3. If the fragment is a single bare Drive ref (F1..F7) → return it.
      4. If the fragment contains state references (^N^D / Cn / Pn) →
         single ref returns bare `^N^D`; multiple → StateCluster{...}.
      5. If the fragment contains Noetic references (^N / CO-N) →
         single ref returns bare `^N`; multiple → NoeticCluster{...}.
      6. Otherwise → None (resolution failed).
    """
    if not text_fragment:
        return None
    lower = text_fragment.strip().lower()

    # Strip trailing punctuation and leading articles for the bare-name
    # check.
    stripped = re.sub(r"^(the\s+|a\s+|an\s+)", "", lower)
    stripped = re.sub(r"[.,;:!?\)]+$", "", stripped).strip()

    if stripped in _CANONICAL_META_SETS:
        return _CANONICAL_META_SETS[stripped]

    # Bare singular Domain code (P/C/E/O) — match against original-case fragment
    cleaned = text_fragment.strip()
    cleaned = re.sub(r"^(the\s+|a\s+|an\s+)", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[.,;:!?\)]+$", "", cleaned).strip()
    if re.fullmatch(r"[PCEO]", cleaned):
        return cleaned

    # Bare singular Drive ref (F1..F7)
    drive_match = re.fullmatch(r"F([1-7])", cleaned)
    if drive_match:
        return cleaned

    # Foundation_1..Foundation_7 (singular Foundation references)
    found_match = re.fullmatch(r"Foundation_[1-7]", cleaned)
    if found_match:
        return cleaned

    # Already-formed cluster expressions appearing literally in prose
    cluster_match = re.search(
        r"(NoeticCluster|StateCluster|StateVariantCluster|RelationCluster|"
        r"NoeticSet|StateSet|StateVariantSet|RelationSet|"
        r"DriveSet|DomainSet|RegisterSet|FoundationSet|SubFoundationSet)"
        r"\s*\{[^}]*\}",
        text_fragment,
    )
    if cluster_match:
        return cluster_match.group(0)

    # Look for explicit state references first (more specific than ^N alone)
    states: list[str] = []
    for match in _STATE_REF.finditer(text_fragment):
        groups = match.groups()
        if groups[0] and groups[1]:  # ^N^D
            states.append(f"^{groups[0]}^{groups[1]}")
        elif groups[2] and groups[3]:  # CO-N^D
            states.append(f"^{groups[2]}^{groups[3]}")
        elif groups[4] and groups[5]:  # Dn shorthand
            states.append(f"^{groups[5]}^{groups[4]}")
    if states:
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique = [s for s in states if not (s in seen or seen.add(s))]
        if len(unique) == 1:
            return unique[0]
        return "StateCluster{" + ", ".join(unique) + "}"

    # Fall back to bare Noetic operators
    noetics: list[str] = []
    for match in _NOETIC_REF.finditer(text_fragment):
        op = match.group(1) or match.group(2)
        noetics.append(f"^{op}")
    if noetics:
        seen2: set[str] = set()
        unique_n = [n for n in noetics if not (n in seen2 or seen2.add(n))]
        if len(unique_n) == 1:
            return unique_n[0]
        return "NoeticCluster{" + ", ".join(unique_n) + "}"

    return None


def _construct_meta_logic_assertion(operation: str, operands: list[str]) -> str:
    """Build a typed assertion string from operation + resolved operands.

    Caller is responsible for validating that operand count matches
    operation arity (binary ops require 2 operands; the assertion ops
    require LHS + RHS in that order).
    """
    if operation in ("Union", "Intersection", "Difference") and len(operands) >= 2:
        symbol = {"Union": "∪", "Intersection": "∩", "Difference": "∖"}[operation]
        return f"{operands[0]} {symbol} {operands[1]}"
    if operation == "Member" and len(operands) >= 2:
        return f"{operands[0]} ∈ {operands[1]}"
    if operation == "NotMember" and len(operands) >= 2:
        return f"{operands[0]} ∉ {operands[1]}"
    if operation == "Subset" and len(operands) >= 2:
        return f"{operands[0]} ⊂ {operands[1]}"
    if operation == "SubsetEq" and len(operands) >= 2:
        return f"{operands[0]} ⊆ {operands[1]}"
    if operation == "Superset" and len(operands) >= 2:
        return f"{operands[0]} ⊃ {operands[1]}"
    if operation == "SupersetEq" and len(operands) >= 2:
        return f"{operands[0]} ⊇ {operands[1]}"
    return ""


def _split_around_keyword(text: str, keyword: str) -> Optional[tuple[str, str]]:
    """Split lower-cased text around the first occurrence of ``keyword``.

    Returns (left_fragment, right_fragment) using the original-case text,
    or None if keyword not found. Used by trigger handlers to extract
    candidate operand fragments.
    """
    lower = text.lower()
    idx = lower.find(keyword)
    if idx < 0:
        return None
    return text[:idx], text[idx + len(keyword):]


def _build_set_op_assertion(op: str, left_frag: str, right_frag: str) -> Optional[str]:
    """Resolve, wrap, compile-validate, and emit a set-op assertion."""
    # Trim right fragment at first sentence-ending punctuation
    right_frag = re.split(r"[.;,]", right_frag, maxsplit=1)[0]
    lhs = _resolve_meta_set_operand(left_frag)
    rhs = _resolve_meta_set_operand(right_frag)
    if not lhs or not rhs:
        return None
    if not _carriers_compatible(lhs, rhs, op):
        return None
    lhs_w = _wrap_singleton_for_set_op(lhs)
    rhs_w = _wrap_singleton_for_set_op(rhs)
    assertion = _construct_meta_logic_assertion(op, [lhs_w, rhs_w])
    if assertion and compile_expression(assertion).valid:
        return assertion
    return None


def _try_union_or_intersection_emission(
    source_text: str,
    *,
    op: str,
    keywords: tuple[str, ...],
    together_keywords: tuple[str, ...],
) -> Optional[str]:
    """Try each "<keyword> A and B" phrasing for ∪/∩."""
    for keyword in keywords:
        split = _split_around_keyword(source_text, keyword)
        if split is None:
            continue
        _, after = split
        conj_split = _split_around_keyword(after, " and ")
        if conj_split is None:
            continue
        left_frag, right_frag = conj_split
        assertion = _build_set_op_assertion(op, left_frag, right_frag)
        if assertion:
            return assertion
    return None


def _try_meta_logic_emission(source_text: str | None) -> Optional[str]:
    """Try to emit a typed meta-logic assertion from explicit prose signals.

    Returns a compiler-admitted assertion string if the prose explicitly
    invokes set-theoretic vocabulary AND operands resolve to canonical
    carriers. Returns None otherwise — caller must fall back to existing
    v7.4-v7.7 emission paths.

    This is conservative by design: the false-fire cost is high (a wrong
    assertion gets propagated as the synthesized notation), the miss cost
    is low (existing emission paths still produce a valid compiled
    expression).
    """
    if not source_text:
        return None
    source_text = _normalize_numeric_meta_refs(source_text)

    # ---- 1. Set-operation triggers (Union / Intersection / Difference) ----
    op = _detect_set_operation_vocabulary(source_text)
    if op is not None:
        if op == "Union":
            assertion = _try_union_or_intersection_emission(
                source_text,
                op="Union",
                keywords=("union of ", "combined set of "),
                together_keywords=(),
            )
            if assertion:
                return assertion
        elif op == "Intersection":
            assertion = _try_union_or_intersection_emission(
                source_text,
                op="Intersection",
                keywords=("intersection of ", "common to both ", "overlap of "),
                together_keywords=(),
            )
            if assertion:
                return assertion
            # "what A and B share" phrasing
            share_pat = re.search(
                r"what\s+(.+?)\s+and\s+(.+?)\s+share\b",
                source_text.lower(),
            )
            if share_pat:
                left_frag = _slice_original_case(source_text, share_pat.group(1))
                right_frag = _slice_original_case(source_text, share_pat.group(2))
                assertion = _build_set_op_assertion("Intersection", left_frag, right_frag)
                if assertion:
                    return assertion
        elif op == "Difference":
            assertion = _try_difference_emission(source_text)
            if assertion:
                return assertion

    # ---- 2. Membership / NotMember triggers ----
    mem_op = _detect_membership_vocabulary(source_text)
    if mem_op is not None:
        assertion = _try_membership_emission(source_text, mem_op)
        if assertion:
            return assertion

    # ---- 3. Subset / Superset triggers ----
    sub_op = _detect_subset_vocabulary(source_text)
    if sub_op is not None:
        assertion = _try_subset_emission(source_text, sub_op)
        if assertion:
            return assertion

    return None


def _wrap_singleton_for_set_op(operand: str) -> str:
    """Promote a bare singleton ref to a typed cluster for ∪/∩/∖.

    Compiler-admitted set operations require typed meta-sets on both sides.
    Bare `^N`, `^N^D`, etc. must be wrapped as singleton clusters.
    Named-meta sets (Noetics, States, ...) and existing clusters pass through.
    """
    if re.fullmatch(r"\^\d", operand):
        return f"NoeticCluster{{{operand}}}"
    if re.fullmatch(r"\^\d\^[PCEO]", operand):
        return f"StateCluster{{{operand}}}"
    if re.fullmatch(r"[PCEO]", operand):
        return f"DomainSet{{{operand}}}"
    if re.fullmatch(r"F[1-7]", operand):
        return f"DriveSet{{{operand}}}"
    return operand


def _carriers_compatible(lhs: str, rhs: str, operation: str) -> bool:
    """Approximate carrier-type compatibility check.

    The compiler enforces this strictly; we filter the obviously incompatible
    pairs here so we don't emit assertions we know will fail. The compile
    check at the end of `_try_meta_logic_emission` is the real safety net.
    """
    def _carrier_kind(s: str) -> str:
        if s.startswith("NoeticCluster") or s.startswith("NoeticSet") or re.fullmatch(r"\^\d", s):
            return "noetic"
        if s.startswith("StateCluster") or s.startswith("StateSet") or re.fullmatch(r"\^\d\^[PCEO]", s):
            return "state"
        if s.startswith("DomainSet"):
            return "domain"
        if s.startswith("DriveSet"):
            return "drive"
        if s.startswith("RegisterSet"):
            return "register"
        if s.startswith("FoundationSet"):
            return "foundation"
        if s.startswith("SubFoundationSet"):
            return "subfoundation"
        if re.fullmatch(r"[PCEO]", s):
            return "domain"
        if re.fullmatch(r"F[1-7]", s):
            return "drive"
        if re.fullmatch(r"Foundation_[1-7]", s):
            return "foundation"
        if s in ("Noetics",):
            return "noetic"
        if s in ("States",):
            return "state"
        if s in ("Domains",):
            return "domain"
        if s in ("Drives",):
            return "drive"
        if s in ("Registers",):
            return "register"
        if s in ("Foundations", "SubFoundations"):
            return "foundation"
        return "unknown"

    lk = _carrier_kind(lhs)
    rk = _carrier_kind(rhs)
    if lk == "unknown" or rk == "unknown":
        return False
    return lk == rk


def _try_difference_emission(source_text: str) -> Optional[str]:
    """Build an A ∖ B assertion from any of the recognized phrasings."""
    lower = source_text.lower()
    # Pattern 1: "everything in A except B" / "all things in A except B"
    pat1 = re.search(
        r"(?:everything|all\s+things|all\s+of)\s+in\s+(.+?)\s+(?:except|excluding|but\s+not)\s+(.+?)(?:[.;,]|$)",
        lower,
    )
    # Pattern 2: "<meta-set> minus|excluding <something>"
    pat2 = re.search(
        r"\b(noetics|domains|states|drives|registers|foundations|subfoundations)"
        r"\s+(?:minus|excluding)\s+(.+?)(?:[.;,]|$)",
        lower,
    )
    # Pattern 3: "all A that aren't B" / "all A that are not B"
    pat3 = re.search(
        r"all\s+(.+?)\s+that\s+(?:aren't|are\s+not|isn't|is\s+not)\s+(.+?)(?:[.;,]|$)",
        lower,
    )
    match_groups: list[tuple[str, str]] = []
    if pat1:
        match_groups.append((pat1.group(1), pat1.group(2)))
    if pat2:
        match_groups.append((pat2.group(1), pat2.group(2)))
    if pat3:
        match_groups.append((pat3.group(1), pat3.group(2)))

    for left_frag, right_frag in match_groups:
        left_orig = _slice_original_case(source_text, left_frag)
        right_orig = _slice_original_case(source_text, right_frag)
        lhs = _resolve_meta_set_operand(left_orig)
        rhs = _resolve_meta_set_operand(right_orig)
        if lhs and rhs and _carriers_compatible(lhs, rhs, "Difference"):
            lhs_wrapped = _wrap_singleton_for_set_op(lhs)
            rhs_wrapped = _wrap_singleton_for_set_op(rhs)
            assertion = _construct_meta_logic_assertion(
                "Difference", [lhs_wrapped, rhs_wrapped]
            )
            if assertion and compile_expression(assertion).valid:
                return assertion
    return None


def _try_membership_emission(source_text: str, op: str) -> Optional[str]:
    """Build a `X ∈ M` / `X ∉ M` assertion from explicit phrasing."""
    lower = source_text.lower()
    set_alt = "|".join(_CANONICAL_META_SETS.keys())
    if op == "Member":
        pat = re.search(
            rf"(.+?)\s+(?:is\s+a\s+member\s+of|belongs\s+to|is\s+in)\s+({set_alt})\b",
            lower,
        )
    else:
        pat = re.search(
            rf"(.+?)\s+(?:is\s+not\s+a\s+member\s+of|isn't\s+a\s+member\s+of|"
            rf"does\s+not\s+belong\s+to|doesn't\s+belong\s+to|"
            rf"is\s+not\s+in|isn't\s+in)\s+({set_alt})\b",
            lower,
        )
    if not pat:
        return None
    left_frag = pat.group(1)
    right_meta = pat.group(2)
    left_orig = _slice_original_case(source_text, left_frag)
    lhs = _resolve_meta_set_operand(left_orig)
    rhs = _CANONICAL_META_SETS.get(right_meta.lower())
    if not lhs or not rhs:
        return None
    # For membership, LHS must be a singular item (^N or ^N^D).
    # Reject cluster wrappers — they'd be subset assertions, not membership.
    if lhs.startswith("NoeticCluster") or lhs.startswith("StateCluster"):
        return None
    assertion = _construct_meta_logic_assertion(op, [lhs, rhs])
    if assertion and compile_expression(assertion).valid:
        return assertion
    return None


def _try_subset_emission(source_text: str, op: str) -> Optional[str]:
    """Build a subset/superset assertion from explicit phrasing."""
    lower = source_text.lower()
    set_alt = "|".join(_CANONICAL_META_SETS.keys())

    if op in ("Subset", "SubsetEq"):
        if op == "SubsetEq":
            pat = re.search(
                rf"(.+?)\s+(?:is\s+a\s+subset\s+of\s+or\s+equals?|"
                rf"is\s+at\s+most)\s+({set_alt})\b",
                lower,
            )
        else:
            pat = re.search(
                rf"(.+?)\s+(?:is\s+contained\s+in|is\s+a\s+subset\s+of|"
                rf"is\s+part\s+of)\s+({set_alt})\b",
                lower,
            )
        if not pat:
            return None
        left_frag = pat.group(1)
        right_meta = pat.group(2)
        left_orig = _slice_original_case(source_text, left_frag)
        lhs = _resolve_meta_set_operand(left_orig)
        rhs = _CANONICAL_META_SETS.get(right_meta.lower())
        if not lhs or not rhs:
            return None
        # Subset/SubsetEq requires a meta-set on the LHS — wrap bare singleton
        # refs into typed clusters before emission.
        lhs_wrapped = _wrap_singleton_for_set_op(lhs)
        assertion = _construct_meta_logic_assertion(op, [lhs_wrapped, rhs])
        if assertion and compile_expression(assertion).valid:
            return assertion
        return None

    # Superset / SupersetEq: "<meta-set> contains [or equals] X"
    if op == "SupersetEq":
        pat = re.search(
            rf"\b({set_alt})\s+(?:contains\s+or\s+equals?|is\s+at\s+least)\s+(.+?)(?:[.;,]|$)",
            lower,
        )
    else:
        pat = re.search(
            rf"\b({set_alt})\s+(?:contains|includes)\s+(.+?)(?:[.;,]|$)",
            lower,
        )
    if not pat:
        return None
    left_meta = pat.group(1)
    right_frag = pat.group(2)
    right_orig = _slice_original_case(source_text, right_frag)
    lhs = _CANONICAL_META_SETS.get(left_meta.lower())
    rhs = _resolve_meta_set_operand(right_orig)
    if not lhs or not rhs:
        return None
    # Superset/SupersetEq requires a meta-set on the RHS — wrap bare singleton
    # refs into typed clusters before emission.
    rhs_wrapped = _wrap_singleton_for_set_op(rhs)
    assertion = _construct_meta_logic_assertion(op, [lhs, rhs_wrapped])
    if assertion and compile_expression(assertion).valid:
        return assertion
    return None


def _slice_original_case(source_text: str, lower_fragment: str) -> str:
    """Return the original-case slice of ``source_text`` that matches
    ``lower_fragment``. Falls back to the lower fragment itself when the
    case-insensitive search fails (rare; only when fragment was synthesized
    rather than excerpted)."""
    needle = lower_fragment.strip()
    if not needle:
        return ""
    haystack = source_text.lower()
    idx = haystack.find(needle)
    if idx < 0:
        return lower_fragment
    return source_text[idx:idx + len(needle)]


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

    # Try meta-logic emission first. On a hit, short-circuit with a typed
    # assertion. On a miss, fall through to the existing v7.4-v7.7 paths
    # exactly as before.
    meta_logic_source = _try_meta_logic_emission(source_text)
    if meta_logic_source:
        artifact = compile_expression(meta_logic_source)
        if artifact.valid:
            registers = _infer_registers(source_text)
            english = _render_english(
                operators, domains, rpm_drives, plain_drives, fractal_classification
            )
            provenance = {
                "operators_found": len(operators),
                "operators": [f"CO-{op}" for op in operators],
                "domains_found": len(domains),
                "domains": domains,
                "rpm_drives": [f"F{d + 1}" for d in rpm_drives],
                "plain_drives": [f"F{d + 1}" for d in plain_drives],
                "flagged_inversions": flagged_inversions,
                "registers": registers,
                "production_recipe": False,
                "register_copresence": False,
                "fractal_classification": fractal_classification,
                "rpm_completeness": round(rpm_completeness, 4),
                "compiler_engine": artifact.engine,
                "compiler_valid": artifact.valid,
                "compiler_error": artifact.error,
                "meta_logic_emission": True,
            }
            return SynthesizedNotation(
                source=meta_logic_source,
                valid=True,
                english=english or meta_logic_source,
                compiler_artifact=artifact.to_dict(),
                provenance=provenance,
            )

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
