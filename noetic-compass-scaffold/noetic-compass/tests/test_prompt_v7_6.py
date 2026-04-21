"""Tests for the v7.6 Production Semantics content in the CAS LLM prompt.

These tests verify that the `CAS_BASE_SYSTEM_PROMPT` and
`CAS_SELF_SCORING_APPENDIX` strings in `api.llm_connectors.base` correctly
contain:

1. The 11 Clarification 9 Section 2 definitions (Production Target Ω,
   Recipe Θ, State Vector S, Theoretical Yield Y_T, Actual Yield Y_A,
   Production Efficiency η, Limiting Reagent L, Excess Capacity ε,
   Leakage Λ, Catalyst κ, Inhibitor ι).
2. The 5 Clarification 9 Section 5 distinctions (Leakage vs Lacunarity,
   Leakage vs Inversion, Recipe vs RPM, Recipe weights vs Drive values,
   Limiting Reagent vs Lacunarity).
3. A Production Analysis optional block in `CAS_SELF_SCORING_APPENDIX`
   with a backward-compat / omission-acceptable note.
4. The v7.5 Register axis content (4 register definitions plus anti-drift
   annotations for `^3` Negative and `^8` Above/Cause) is still present.
5. The 10 authoritative Noetic definitions still verbatim-aligned.
6. v7.7 Clarification 10 operator discipline is not violated by v7.6
   content (no same-Noetic multi-register `×` without emergent-result
   specification).
7. Prompt-level well-formedness (non-empty strings, expected section
   headers, backward-compat alias, builder behaviour).

These tests do NOT modify the prompt; they only verify its contents.
"""

from __future__ import annotations

import re

import pytest

from api.llm_connectors.base import (
    CAS_BASE_SYSTEM_PROMPT,
    CAS_SELF_SCORING_APPENDIX,
    CAS_SYSTEM_PROMPT,
    build_cas_system_prompt,
)
from api.notation.compiler import VALID_REGISTERS


# ---------------------------------------------------------------------------
# Shared expectation tables
# ---------------------------------------------------------------------------


# Clarification 9 Section 2 — 11 definitions.
# Each entry: (concept label, list of keyword fragments that MUST all appear
# in CAS_BASE_SYSTEM_PROMPT for the definition to count as present).
# Keywords chosen to be verbatim substrings of the definition text; we assert
# presence (not exclusivity) so that natural prose variation around the
# definition is tolerated.
PRODUCTION_DEFINITIONS: list[tuple[str, list[str]]] = [
    (
        "Production Target (Ω)",
        ["Production Target", "Ω", "specified outcome"],
    ),
    (
        "Recipe (Θ)",
        ["Recipe", "Θ", "proportional weighting", "prerequisite"],
    ),
    (
        "State Vector (S)",
        ["State Vector", "current activation profile", "available quantities"],
    ),
    (
        "Theoretical Yield (Y_T)",
        ["Theoretical Yield", "Y_T", "min_i(xᵢ / aᵢ)"],
    ),
    (
        "Actual Yield (Y_A)",
        ["Actual Yield", "Y_A", "empirically"],
    ),
    (
        "Production Efficiency (η)",
        ["Production Efficiency", "η", "Y_A / Y_T", "[0, 1]"],
    ),
    (
        "Limiting Reagent (L)",
        ["Limiting Reagent", "bottleneck"],
    ),
    (
        "Excess Capacity (ε)",
        ["Excess Capacity", "ε", "unused prerequisite"],
    ),
    (
        "Leakage / Side-Reaction (Λ)",
        [
            "Leakage",
            "Side-Reaction",
            "Λ",
            "prerequisite present but producing wrong product",
        ],
    ),
    (
        "Catalyst (κ)",
        ["Catalyst", "κ", "without being", "consumed"],
    ),
    (
        "Inhibitor (ι)",
        ["Inhibitor", "ι", "reducing conversion efficiency"],
    ),
]


# Clarification 9 Section 5 — 5 distinctions.
# Each entry: (distinction label, list of keyword phrases that MUST all
# appear in the prompt's distinctions block).
PRODUCTION_DISTINCTIONS: list[tuple[str, list[str]]] = [
    (
        "Leakage vs Lacunarity",
        ["Leakage vs Lacunarity", "ABSENT", "PRESENT but producing wrong product"],
    ),
    (
        "Leakage vs Inversion",
        ["Leakage vs Inversion", "shadow", "diverted to side product"],
    ),
    (
        "Recipe vs RPM",
        [
            "Recipe vs RPM",
            "sequential",
            "proportional",
            "correct sequence",
            "correct proportion",
        ],
    ),
    (
        "Recipe weights vs Drive values",
        [
            "Recipe weights vs Drive values",
            "current activation",
            "outcome-specific requirement",
        ],
    ),
    (
        "Limiting Reagent vs Lacunarity",
        [
            "Limiting Reagent vs Lacunarity",
            "state-space voids",
            "proportional bottlenecks",
        ],
    ),
]


# Authoritative 10 Noetic definitions — key phrases per Clarification 1.
# Each entry: (operator tag, list of verbatim phrases that MUST appear).
NOETIC_DEFINITION_KEYWORDS: list[tuple[str, list[str]]] = [
    ("CO-0 Idea", ["CO-0 Idea", "all things in and outside the Mind"]),
    (
        "CO-1 Mind",
        [
            "CO-1 Mind",
            "various degrees of awareness",
            "processes, stores, outputs, and intakes Ideas",
        ],
    ),
    (
        "CO-2 Positive",
        ["CO-2 Positive", "affinity for", "attracted toward"],
    ),
    (
        "CO-3 Negative",
        ["CO-3 Negative", "adverse to", "repelled by"],
    ),
    (
        "CO-4 Vibration",
        ["CO-4 Vibration", "resonates with", "impression"],
    ),
    (
        "CO-5 Female",
        ["CO-5 Female", "impregnated with an Idea", "Mind is composed of"],
    ),
    (
        "CO-6 Male",
        ["CO-6 Male", "Idea impregnated with another Idea", "Idea is composed of"],
    ),
    (
        "CO-7 Rhythm",
        ["CO-7 Rhythm", "rate and pattern", "entraining/conditioning"],
    ),
    (
        "CO-8 Above/Cause",
        ["CO-8 Above/Cause", "triggers a different Idea"],
    ),
    (
        "CO-9 Below/Effect",
        ["CO-9 Below/Effect", "Idea brought to Mind"],
    ),
]


# ---------------------------------------------------------------------------
# 1. Verbatim definitions (Clarification 9 Section 2)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label,keywords",
    PRODUCTION_DEFINITIONS,
    ids=[label for label, _ in PRODUCTION_DEFINITIONS],
)
def test_v7_6_definition_present_in_base_prompt(label: str, keywords: list[str]):
    """Each Clarification 9 Section 2 definition keyword-set is present."""
    missing = [kw for kw in keywords if kw not in CAS_BASE_SYSTEM_PROMPT]
    assert not missing, (
        f"v7.6 definition {label!r} missing expected keywords "
        f"from CAS_BASE_SYSTEM_PROMPT: {missing}"
    )


def test_v7_6_all_eleven_definitions_covered():
    """Exactly the 11 Clarification 9 Section 2 concepts are tested."""
    assert len(PRODUCTION_DEFINITIONS) == 11, (
        "PRODUCTION_DEFINITIONS table must hold all 11 Clarification 9 "
        "Section 2 definitions (Production Target, Recipe, State Vector, "
        "Theoretical Yield, Actual Yield, Production Efficiency, Limiting "
        "Reagent, Excess Capacity, Leakage, Catalyst, Inhibitor)."
    )


# ---------------------------------------------------------------------------
# 2. Verbatim distinctions (Clarification 9 Section 5)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label,keywords",
    PRODUCTION_DISTINCTIONS,
    ids=[label for label, _ in PRODUCTION_DISTINCTIONS],
)
def test_v7_6_distinction_present_in_base_prompt(label: str, keywords: list[str]):
    """Each Clarification 9 Section 5 distinction keyword-set is present."""
    missing = [kw for kw in keywords if kw not in CAS_BASE_SYSTEM_PROMPT]
    assert not missing, (
        f"v7.6 distinction {label!r} missing expected keywords "
        f"from CAS_BASE_SYSTEM_PROMPT: {missing}"
    )


def test_v7_6_all_five_distinctions_covered():
    """Exactly the 5 Clarification 9 Section 5 distinctions are tested."""
    assert len(PRODUCTION_DISTINCTIONS) == 5, (
        "PRODUCTION_DISTINCTIONS table must hold all 5 Clarification 9 "
        "Section 5 distinctions (Leakage vs Lacunarity, Leakage vs "
        "Inversion, Recipe vs RPM, Recipe weights vs Drive values, "
        "Limiting Reagent vs Lacunarity)."
    )


# ---------------------------------------------------------------------------
# 3. Optional Production Analysis block in CAS_SELF_SCORING_APPENDIX
# ---------------------------------------------------------------------------


def test_self_scoring_appendix_has_production_analysis_block():
    """Appendix offers an optional Production Analysis block structure."""
    appendix = CAS_SELF_SCORING_APPENDIX
    assert "Production Analysis" in appendix, (
        "CAS_SELF_SCORING_APPENDIX must describe an optional "
        "`Production Analysis:` block for v7.6 recipe/yield observations."
    )
    # Required structural fields of the block template.
    for marker in ("Target (Ω)", "Recipe (Θ)", "Limiting Reagent (L)", "Efficiency (η)"):
        assert marker in appendix, (
            f"CAS_SELF_SCORING_APPENDIX Production Analysis block missing "
            f"the {marker!r} field."
        )


def test_self_scoring_appendix_production_analysis_is_optional():
    """Appendix asserts the block is OPTIONAL and omission is acceptable."""
    appendix = CAS_SELF_SCORING_APPENDIX
    assert "OPTIONAL" in appendix, (
        "CAS_SELF_SCORING_APPENDIX must mark the Production Analysis "
        "block as OPTIONAL."
    )
    assert "backward-compatible" in appendix.lower() or "backward compatible" in appendix.lower(), (
        "CAS_SELF_SCORING_APPENDIX must note backward compatibility for "
        "responses omitting the Production Analysis block."
    )
    # Explicit acceptable-omission phrasing.
    assert "Omission" in appendix or "omission" in appendix, (
        "CAS_SELF_SCORING_APPENDIX must explicitly state that omission "
        "of the Production Analysis block is acceptable."
    )


# ---------------------------------------------------------------------------
# 4. v7.5 Register section unchanged
# ---------------------------------------------------------------------------


def test_v7_5_register_section_header_present():
    """The Phenomenological Register v7.5 section header is still present."""
    assert "Phenomenological Register (CAS v7.5)" in CAS_BASE_SYSTEM_PROMPT, (
        "v7.6 addition must not remove the v7.5 Phenomenological Register "
        "section."
    )


@pytest.mark.parametrize(
    "register_label,keywords",
    [
        ("|T Transcendent", ["|T", "Transcendent Register", "High-abstraction"]),
        ("|A Analytical", ["|A", "Analytical Register", "sequential, logical"]),
        ("|f Affective", ["|f", "Affective Register", "Value-laden"]),
        ("|E Embodied", ["|E", "Embodied Register", "Sensorimotor"]),
    ],
    ids=["T", "A", "f", "E"],
)
def test_v7_5_register_definitions_present(register_label: str, keywords: list[str]):
    """Each of the 4 v7.5 Register definitions is still in the prompt."""
    missing = [kw for kw in keywords if kw not in CAS_BASE_SYSTEM_PROMPT]
    assert not missing, (
        f"v7.5 Register definition {register_label!r} missing expected "
        f"keywords: {missing}"
    )


def test_v7_5_register_values_match_compiler():
    """Register values advertised in prompt match VALID_REGISTERS single source."""
    # The prompt explicitly states R ∈ {T, A, f, E}.
    assert "R ∈ {T, A, f, E}" in CAS_BASE_SYSTEM_PROMPT, (
        "Prompt must advertise register grammar R ∈ {T, A, f, E} consistent "
        "with VALID_REGISTERS in api.notation.compiler."
    )
    # Each register letter referenced in prompt must be in the compiler's
    # VALID_REGISTERS tuple.
    for r in ("T", "A", "f", "E"):
        assert r in VALID_REGISTERS, (
            f"Register {r!r} referenced in prompt but not in compiler's "
            f"VALID_REGISTERS={VALID_REGISTERS}."
        )


def test_v7_5_anti_drift_annotations_present():
    """Anti-drift annotations for ^3 Negative and ^8 Above/Cause present."""
    # ^3 visceral-not-analytical.
    assert "CO-3 is VISCERAL, not analytical" in CAS_BASE_SYSTEM_PROMPT, (
        "^3 Negative visceral-not-analytical anti-drift annotation missing."
    )
    # ^8 associative-not-deductive.
    assert "CO-8 is ASSOCIATIVE, not deductive" in CAS_BASE_SYSTEM_PROMPT, (
        "^8 Above/Cause associative-not-deductive anti-drift annotation missing."
    )


# ---------------------------------------------------------------------------
# 5. v7.4 Noetic definitions unchanged
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "operator,keywords",
    NOETIC_DEFINITION_KEYWORDS,
    ids=[op for op, _ in NOETIC_DEFINITION_KEYWORDS],
)
def test_v7_4_noetic_definition_present(operator: str, keywords: list[str]):
    """Each authoritative Noetic definition (Clarification 1) still present."""
    missing = [kw for kw in keywords if kw not in CAS_BASE_SYSTEM_PROMPT]
    assert not missing, (
        f"Noetic {operator!r} authoritative definition missing expected "
        f"keywords: {missing}"
    )


def test_v7_4_involution_pairs_and_self_duals_present():
    """Involution pairs and self-duals are still advertised."""
    for marker in (
        "CO-2 Positive ↔ CO-3 Negative",
        "CO-5 Female ↔ CO-6 Male",
        "CO-8 Above/Cause ↔ CO-9 Below/Effect",
        "Self-duals: CO-0 Idea, CO-1 Mind, CO-4 Vibration, CO-7 Rhythm",
    ):
        assert marker in CAS_BASE_SYSTEM_PROMPT, (
            f"Involution/self-dual declaration missing: {marker!r}"
        )


# ---------------------------------------------------------------------------
# 6. v7.7 Clarification 10 discipline — non-violation check
# ---------------------------------------------------------------------------


# Regex matching `^n^D|R × ^n^D|R ...` style same-Noetic multi-register
# multiplication. This is the pattern Clarification 10 Section 4
# declares invalid unless an emergent result is specified.
#
# Structure: a Noetic+Domain+Register atom, followed by ` × ` (U+00D7),
# followed by another atom whose Noetic+Domain matches the first one.
_NOETIC_REGISTER_ATOM = re.compile(
    r"\^(?P<n>\d)\^(?P<d>[PCEO])\|(?P<r>[TAfE])"
)


def test_v7_7_no_same_noetic_multi_register_cross_product():
    """No `^n^D|R × ^n^D|R` in prompt without emergent-result spec.

    Clarification 10 Section 4 declares same-Noetic multi-register `×`
    expressions invalid by default; they must be rewritten to `+` (for
    co-presence) or `|⟨…⟩` (for specification), or must include an
    explicit emergent result. This test scans the v7.6 prompt for any
    such expression and fails if found.
    """
    prompt = CAS_BASE_SYSTEM_PROMPT

    # Scan every `×` occurrence and inspect a window on either side.
    violations: list[str] = []
    for match in re.finditer(r"×", prompt):
        start = max(0, match.start() - 40)
        end = min(len(prompt), match.end() + 40)
        window = prompt[start:end]

        # Find Noetic+Domain+Register atoms on either side of the ×.
        left_atoms = list(_NOETIC_REGISTER_ATOM.finditer(prompt[start : match.start()]))
        right_atoms = list(_NOETIC_REGISTER_ATOM.finditer(prompt[match.end() : end]))

        if not left_atoms or not right_atoms:
            continue  # not a state-algebra × between register-enriched atoms

        left = left_atoms[-1]  # nearest on left
        right = right_atoms[0]  # nearest on right

        if left.group("n") == right.group("n") and left.group("d") == right.group("d"):
            # Same Noetic AND same Domain — check for emergent-result note.
            # Accept if window contains an explicit "= X" after the sequence
            # or an "Ω" (emergent result) or a "|⟨" specification nearby.
            post = prompt[match.end() : min(len(prompt), match.end() + 80)]
            if "=" not in post and "Ω" not in post and "|⟨" not in post:
                violations.append(window.strip())

    assert not violations, (
        "Clarification 10 Section 4 violation in CAS_BASE_SYSTEM_PROMPT: "
        f"same-Noetic multi-register `×` without emergent-result spec: "
        f"{violations}"
    )


def test_v7_7_tks_validation_heuristic_documented_in_prompt():
    """Clarification 10 Section 7 TKS validation heuristic is present in prompt.

    Clarification 10 Section 7's TKS validation heuristic states:
    - `+` substitutes as "associates with"
    - `×` substitutes as "intensifies through"

    When v7.7 content is present in the prompt (per rollout track (f), commit
    adding Register Operator Discipline section), this substitution-test
    guidance must be documented so LLMs applying the discipline have the
    heuristic available. This test verifies the heuristic text is present.

    Rule 4 enforcement (that no bare same-Noetic multi-register `×` lacks
    an emergent-result spec) is delegated entirely to
    `test_v7_7_no_same_noetic_multi_register_cross_product` above, which
    correctly handles disciplined `×` patterns: (a) different-state
    integration with `=` assignment, (b) same-state with named emergent
    result (`Ω`, `TF`, etc.) within 80 chars, and (c) negative examples
    clearly marked with rewrite hints (`|⟨…⟩` or `+`) within 80 chars.

    Predecessor note: this test previously implemented a whitelist that
    pre-emptively forbade `×` occurrences beyond axis-cardinality products
    and English section headings, under the pre-v7.7 assumption that the
    prompt carried no Clarification 10 content. Once v7.7 content lands,
    that whitelist becomes obsolete — disciplined `×` patterns and
    correctly-marked negative examples must be permitted. Rule 4
    enforcement moved entirely to the sibling discipline scanner.
    """
    prompt = CAS_BASE_SYSTEM_PROMPT
    # Heuristic substitution phrases per Clarification 10 Section 7.
    assert "associates with" in prompt, (
        "CAS_BASE_SYSTEM_PROMPT must document the `+` → 'associates with' "
        "substitution per Clarification 10 Section 7 TKS validation heuristic."
    )
    assert "intensifies through" in prompt, (
        "CAS_BASE_SYSTEM_PROMPT must document the `×` → 'intensifies through' "
        "substitution per Clarification 10 Section 7 TKS validation heuristic."
    )


def test_v7_6_recipe_notation_uses_plus_for_prerequisite_addition():
    """Recipe notation uses `+` for prerequisite addition (not `×`)."""
    prompt = CAS_BASE_SYSTEM_PROMPT
    # Clarification 9 Section 3 recipe notation:
    # Θ(Ω) = a₁·X₁ + a₂·X₂ + ... + aₙ·Xₙ → Ω
    # The prompt must show the `+` form.
    assert "a₁·X₁ + a₂·X₂" in prompt, (
        "v7.6 recipe notation must use `+` for prerequisite addition per "
        "Clarification 9 Section 3 (syntactic co-presence, consistent with "
        "Clarification 10)."
    )


# ---------------------------------------------------------------------------
# 7. Prompt-level well-formedness
# ---------------------------------------------------------------------------


def test_base_prompt_is_non_empty_string():
    """CAS_BASE_SYSTEM_PROMPT is a non-empty string."""
    assert isinstance(CAS_BASE_SYSTEM_PROMPT, str)
    assert CAS_BASE_SYSTEM_PROMPT.strip(), "CAS_BASE_SYSTEM_PROMPT must be non-empty."


def test_self_scoring_appendix_is_non_empty_string():
    """CAS_SELF_SCORING_APPENDIX is a non-empty string."""
    assert isinstance(CAS_SELF_SCORING_APPENDIX, str)
    assert CAS_SELF_SCORING_APPENDIX.strip(), (
        "CAS_SELF_SCORING_APPENDIX must be non-empty."
    )


def test_base_prompt_has_expected_section_headers():
    """CAS_BASE_SYSTEM_PROMPT contains the three expected section headers."""
    # v7.4 Noetic framing is the implicit first section (no banner).
    # v7.5 Register section banner.
    assert "Phenomenological Register (CAS v7.5)" in CAS_BASE_SYSTEM_PROMPT
    # v7.6 Production Semantics section banner.
    assert "Production Semantics (CAS v7.6)" in CAS_BASE_SYSTEM_PROMPT
    # 10 Noetics header.
    assert "The 10 Noetics" in CAS_BASE_SYSTEM_PROMPT


def test_backward_compatible_alias():
    """CAS_SYSTEM_PROMPT alias equals CAS_BASE_SYSTEM_PROMPT."""
    assert CAS_SYSTEM_PROMPT == CAS_BASE_SYSTEM_PROMPT, (
        "Legacy `CAS_SYSTEM_PROMPT` alias must still equal "
        "`CAS_BASE_SYSTEM_PROMPT` for backward compatibility."
    )


def test_build_cas_system_prompt_includes_appendix_when_requested():
    """`build_cas_system_prompt(include_inline_scores=True)` appends appendix."""
    without = build_cas_system_prompt()
    with_appendix = build_cas_system_prompt(include_inline_scores=True)
    assert without == CAS_BASE_SYSTEM_PROMPT
    assert with_appendix == CAS_BASE_SYSTEM_PROMPT + CAS_SELF_SCORING_APPENDIX
    # Production Analysis block only becomes available when the appendix is
    # included — it does not leak into the base prompt.
    assert "Production Analysis" not in without
    assert "Production Analysis" in with_appendix


def test_v7_6_section_follows_v7_5_section():
    """v7.6 section appears AFTER the v7.5 section in the prompt."""
    v75_idx = CAS_BASE_SYSTEM_PROMPT.find("Phenomenological Register (CAS v7.5)")
    v76_idx = CAS_BASE_SYSTEM_PROMPT.find("Production Semantics (CAS v7.6)")
    assert v75_idx != -1 and v76_idx != -1
    assert v75_idx < v76_idx, (
        "Prompt section ordering must be v7.4 Noetics → v7.5 Register → "
        "v7.6 Production Semantics."
    )


def test_v7_6_optional_and_backward_compatible_markers():
    """v7.6 section advertises OPTIONAL and backward-compat."""
    prompt = CAS_BASE_SYSTEM_PROMPT
    # Find the v7.6 section slice.
    v76_start = prompt.find("Production Semantics (CAS v7.6)")
    assert v76_start != -1
    v76_slice = prompt[v76_start:]
    assert "OPTIONAL" in v76_slice, (
        "v7.6 section must declare production semantics OPTIONAL."
    )
    assert "Backward compatibility" in v76_slice or "backward-compatible" in v76_slice.lower(), (
        "v7.6 section must declare backward compatibility with v7.5."
    )
