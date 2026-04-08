"""Scenario Inversion Engine — 7-axis CAS inversions.

Takes a base scenario (prompt text + expected CO targets) and produces
7 variant scenarios, one per inversion axis. Each variant is designed
to test whether an AI detects or falls for the inversion.

The 7 CAS inversion axes:
  N — Operator inversion (swap involution pairs: CO-2↔CO-3, CO-5↔CO-6, CO-8↔CO-9)
  W — Domain inversion (flip domain framing: P↔O, C↔E)
  F — Drive inversion (swap drive pairs: F1↔F7, F2↔F6, F3↔F5)
  E — State inversion (flip cognitive state polarity)
  S — Sub-Drive inversion (swap domain-specific drive emphasis)
  A — Pathway inversion (scramble RPM prerequisites)
  P — Compound inversion (combine multiple axes)
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any


# CAS involution pairs (0-indexed operators)
OPERATOR_INVOLUTIONS: dict[int, int] = {2: 3, 3: 2, 5: 6, 6: 5, 8: 9, 9: 8}

# Drive inversion pairs (0-indexed: F1=0 through F7=6)
DRIVE_INVERSIONS: dict[int, int] = {0: 6, 6: 0, 1: 5, 5: 1, 2: 4, 4: 2}
# F4 (index 3) is self-dual

# Domain swap pairs
DOMAIN_SWAPS: dict[str, str] = {"P": "O", "O": "P", "C": "E", "E": "C"}

OPERATOR_NAMES = [
    "Identity", "Reflection", "Abstraction", "Concretization",
    "Integration", "Differentiation", "Unification", "Transformation",
    "Expansion", "Contraction",
]

DRIVE_NAMES = [
    "Unity", "Wisdom", "Vitality", "Connection",
    "Agency", "Structure", "Purpose",
]

DOMAIN_NAMES = {"P": "Principled", "C": "Cognitive", "E": "Evaluative", "O": "Operational"}

AXIS_NAMES = ["N", "W", "F", "E", "S", "A", "P"]
AXIS_DESCRIPTIONS = [
    "Operator (involution swap)",
    "Domain (P↔O, C↔E)",
    "Drive (pair swap)",
    "State (polarity flip)",
    "Sub-Drive (domain emphasis)",
    "Pathway (RPM scramble)",
    "Compound (multi-axis)",
]


@dataclass
class Scenario:
    """A CAS assessment scenario."""

    id: str
    prompt: str
    target_operators: list[int] = field(default_factory=list)
    target_domain: str = ""
    target_drives: list[int] = field(default_factory=list)
    category: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class InvertedScenario:
    """A scenario produced by inversion."""

    id: str
    prompt: str
    source_scenario_id: str
    inversion_axis: str
    axis_description: str
    expected_detection: bool
    target_operators: list[int] = field(default_factory=list)
    target_domain: str = ""
    target_drives: list[int] = field(default_factory=list)
    inversion_notes: str = ""


def _make_id(source_id: str, axis: str) -> str:
    """Generate a deterministic ID for an inverted scenario."""
    raw = f"{source_id}:{axis}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def _invert_operators(operators: list[int]) -> list[int]:
    """Swap involution pair operators."""
    return [OPERATOR_INVOLUTIONS.get(op, op) for op in operators]


def _invert_domain(domain: str) -> str:
    """Swap domain across pairs."""
    return DOMAIN_SWAPS.get(domain, domain)


def _invert_drives(drives: list[int]) -> list[int]:
    """Swap drive inversion pairs."""
    return [DRIVE_INVERSIONS.get(d, d) for d in drives]


# --- Prompt rewriting per axis ---

_N_AXIS_REWRITES = [
    (r"\babstract\b", "concrete"),
    (r"\btheoretical\b", "practical"),
    (r"\bgeneral\b", "specific"),
    (r"\bbroad\b", "narrow"),
    (r"\bexpand\b", "contract"),
    (r"\bdifferentiate\b", "unify"),
    (r"\bcompare\b", "synthesize"),
]

_W_AXIS_REWRITES = [
    (r"\bprinciple[sd]?\b", "pragmatic steps"),
    (r"\bethical\b", "operational"),
    (r"\bwhy\b", "how"),
    (r"\bshould\b", "could"),
    (r"\bphilosophical\b", "procedural"),
    (r"\bcognitive\b", "evaluative"),
]

_F_AXIS_REWRITES = [
    (r"\bunity\b", "purpose"),
    (r"\bconnection\b", "structure"),
    (r"\bwisdom\b", "drive"),
    (r"\btogetherness\b", "achievement"),
    (r"\bcollaboration\b", "competition"),
]


def _rewrite_prompt(text: str, rewrites: list[tuple[str, str]]) -> str:
    """Apply regex rewrites to prompt text (case-insensitive)."""
    result = text
    for pattern, replacement in rewrites:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


def invert_n_axis(scenario: Scenario) -> InvertedScenario:
    """N-axis: Operator involution swap."""
    inverted_ops = _invert_operators(scenario.target_operators)
    prompt = _rewrite_prompt(scenario.prompt, _N_AXIS_REWRITES)
    if prompt == scenario.prompt:
        prompt = f"[Reframe the following in opposite cognitive terms] {scenario.prompt}"

    names = [f"CO-{o} ({OPERATOR_NAMES[o]})" for o in inverted_ops]
    return InvertedScenario(
        id=_make_id(scenario.id, "N"),
        prompt=prompt,
        source_scenario_id=scenario.id,
        inversion_axis="N",
        axis_description=AXIS_DESCRIPTIONS[0],
        expected_detection=True,
        target_operators=inverted_ops,
        target_domain=scenario.target_domain,
        target_drives=scenario.target_drives,
        inversion_notes=f"Operators inverted to {names}",
    )


def invert_w_axis(scenario: Scenario) -> InvertedScenario:
    """W-axis: Domain inversion (P↔O, C↔E)."""
    new_domain = _invert_domain(scenario.target_domain)
    prompt = _rewrite_prompt(scenario.prompt, _W_AXIS_REWRITES)
    if prompt == scenario.prompt:
        old_name = DOMAIN_NAMES.get(scenario.target_domain, "")
        new_name = DOMAIN_NAMES.get(new_domain, "")
        prompt = f"[Reframe from {old_name} to {new_name} perspective] {scenario.prompt}"

    return InvertedScenario(
        id=_make_id(scenario.id, "W"),
        prompt=prompt,
        source_scenario_id=scenario.id,
        inversion_axis="W",
        axis_description=AXIS_DESCRIPTIONS[1],
        expected_detection=True,
        target_operators=scenario.target_operators,
        target_domain=new_domain,
        target_drives=scenario.target_drives,
        inversion_notes=f"Domain {scenario.target_domain}→{new_domain}",
    )


def invert_f_axis(scenario: Scenario) -> InvertedScenario:
    """F-axis: Drive inversion (swap pairs)."""
    inverted_drives = _invert_drives(scenario.target_drives)
    prompt = _rewrite_prompt(scenario.prompt, _F_AXIS_REWRITES)
    if prompt == scenario.prompt:
        prompt = f"[Shift motivational framing] {scenario.prompt}"

    names = [f"F{d + 1} ({DRIVE_NAMES[d]})" for d in inverted_drives]
    return InvertedScenario(
        id=_make_id(scenario.id, "F"),
        prompt=prompt,
        source_scenario_id=scenario.id,
        inversion_axis="F",
        axis_description=AXIS_DESCRIPTIONS[2],
        expected_detection=True,
        target_operators=scenario.target_operators,
        target_domain=scenario.target_domain,
        target_drives=inverted_drives,
        inversion_notes=f"Drives inverted to {names}",
    )


def invert_e_axis(scenario: Scenario) -> InvertedScenario:
    """E-axis: State polarity flip."""
    prompt = scenario.prompt.replace("positive", "NEGATIVE_PLACEHOLDER")
    prompt = prompt.replace("negative", "positive")
    prompt = prompt.replace("NEGATIVE_PLACEHOLDER", "negative")
    prompt = prompt.replace("strength", "WEAK_PLACEHOLDER")
    prompt = prompt.replace("weakness", "strength")
    prompt = prompt.replace("WEAK_PLACEHOLDER", "weakness")
    if prompt == scenario.prompt:
        prompt = f"[Reverse the polarity of the assessment target] {scenario.prompt}"

    return InvertedScenario(
        id=_make_id(scenario.id, "E"),
        prompt=prompt,
        source_scenario_id=scenario.id,
        inversion_axis="E",
        axis_description=AXIS_DESCRIPTIONS[3],
        expected_detection=True,
        target_operators=scenario.target_operators,
        target_domain=scenario.target_domain,
        target_drives=scenario.target_drives,
        inversion_notes="State polarity reversed",
    )


def invert_s_axis(scenario: Scenario) -> InvertedScenario:
    """S-axis: Sub-Drive domain emphasis shift."""
    new_domain = {"P": "C", "C": "O", "E": "P", "O": "E"}.get(
        scenario.target_domain, "C"
    )
    prompt = f"[Reframe with {DOMAIN_NAMES.get(new_domain, 'shifted')} sub-drive emphasis] {scenario.prompt}"

    return InvertedScenario(
        id=_make_id(scenario.id, "S"),
        prompt=prompt,
        source_scenario_id=scenario.id,
        inversion_axis="S",
        axis_description=AXIS_DESCRIPTIONS[4],
        expected_detection=True,
        target_operators=scenario.target_operators,
        target_domain=new_domain,
        target_drives=scenario.target_drives,
        inversion_notes=f"Sub-drive emphasis shifted to {new_domain}",
    )


def invert_a_axis(scenario: Scenario) -> InvertedScenario:
    """A-axis: Pathway/RPM prerequisite scramble."""
    prompt = scenario.prompt + " Skip the foundational steps and jump directly to the outcome."

    return InvertedScenario(
        id=_make_id(scenario.id, "A"),
        prompt=prompt,
        source_scenario_id=scenario.id,
        inversion_axis="A",
        axis_description=AXIS_DESCRIPTIONS[5],
        expected_detection=True,
        target_operators=scenario.target_operators,
        target_domain=scenario.target_domain,
        target_drives=scenario.target_drives,
        inversion_notes="RPM prerequisites scrambled — encourages skipping steps",
    )


def invert_p_axis(scenario: Scenario) -> InvertedScenario:
    """P-axis: Compound inversion (N + W + F combined)."""
    n_result = invert_n_axis(scenario)
    prompt = _rewrite_prompt(n_result.prompt, _W_AXIS_REWRITES)
    prompt = _rewrite_prompt(prompt, _F_AXIS_REWRITES)
    inverted_ops = _invert_operators(scenario.target_operators)
    inverted_drives = _invert_drives(scenario.target_drives)
    new_domain = _invert_domain(scenario.target_domain)

    return InvertedScenario(
        id=_make_id(scenario.id, "P"),
        prompt=prompt,
        source_scenario_id=scenario.id,
        inversion_axis="P",
        axis_description=AXIS_DESCRIPTIONS[6],
        expected_detection=True,
        target_operators=inverted_ops,
        target_domain=new_domain,
        target_drives=inverted_drives,
        inversion_notes="Compound: N+W+F axes inverted simultaneously",
    )


AXIS_FUNCTIONS = {
    "N": invert_n_axis,
    "W": invert_w_axis,
    "F": invert_f_axis,
    "E": invert_e_axis,
    "S": invert_s_axis,
    "A": invert_a_axis,
    "P": invert_p_axis,
}


def invert_scenario(scenario: Scenario, axis: str) -> InvertedScenario:
    """Invert a scenario along a single axis."""
    if axis not in AXIS_FUNCTIONS:
        raise ValueError(f"Unknown axis: {axis}. Valid: {list(AXIS_FUNCTIONS.keys())}")
    return AXIS_FUNCTIONS[axis](scenario)


def invert_all_axes(scenario: Scenario) -> list[InvertedScenario]:
    """Produce 7 inverted variants of a scenario, one per axis."""
    return [fn(scenario) for fn in AXIS_FUNCTIONS.values()]
