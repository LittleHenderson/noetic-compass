"""Round-trip verification for CAS training data.

Catches LLM hallucinations by feeding generated English back through the
CAS signal analyzer and compiler, then comparing the re-extracted scores
against the original ground truth.

This module is used when LLM providers generate the English text.
For template-based generation, verification is less critical but
still useful as a quality check.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re


@dataclass
class VerificationResult:
    accepted: bool
    confidence: float
    matches: int = 0
    total: int = 4
    reasons: list[str] = field(default_factory=list)
    detected_operators: list[int] = field(default_factory=list)
    detected_domains: list[str] = field(default_factory=list)
    detected_drives: list[int] = field(default_factory=list)


def _extract_operators(expression: str) -> list[int]:
    return sorted(set(int(m.group(1)) for m in re.finditer(r"CO-(\d+)", expression)))


def _extract_domains(expression: str) -> list[str]:
    return sorted(set(m.group(1) for m in re.finditer(r"\^([PCEO])", expression)))


def _extract_drives(expression: str) -> list[int]:
    return sorted(set(int(m.group(1)) for m in re.finditer(r"F(\d)", expression) if 1 <= int(m.group(1)) <= 7))


def _top_n(scores: list[float], n: int) -> list[int]:
    indexed = sorted(enumerate(scores), key=lambda x: -x[1])
    return [i for i, _ in indexed[:n]]


def verify_round_trip(
    original_expression: str,
    signal_operator_scores: list[float],
    signal_domain_scores: list[float],
    signal_drive_scores: list[float],
) -> VerificationResult:
    """Compare original expression targets against re-extracted signals.

    Acceptance criteria (3 of 4 must match):
    1. OPERATOR MATCH: top detected operators include the expression operators
    2. DOMAIN MATCH: dominant detected domains match expression domains
    3. DRIVE MATCH: at least one drive matches
    4. STRUCTURAL MATCH: descent/division patterns detected
    """
    expected_ops = _extract_operators(original_expression)
    expected_domains = _extract_domains(original_expression)
    expected_drives = _extract_drives(original_expression)
    has_descent = "->" in original_expression
    has_division = " / " in original_expression

    matches = 0
    reasons: list[str] = []

    # 1. Operator match
    top_ops = _top_n(signal_operator_scores, max(3, len(expected_ops)))
    op_overlap = len(set(expected_ops) & set(top_ops))
    if op_overlap >= max(1, int(len(expected_ops) * 0.6)):
        matches += 1
    else:
        reasons.append(f"Operator mismatch: expected {expected_ops}, top detected {top_ops}")

    # 2. Domain match
    dom_map = {0: "P", 1: "C", 2: "E", 3: "O"}
    top_doms = [dom_map[i] for i in _top_n(signal_domain_scores, 2)]
    dom_overlap = len(set(expected_domains) & set(top_doms))
    if dom_overlap >= 1:
        matches += 1
    else:
        reasons.append(f"Domain mismatch: expected {expected_domains}, detected {top_doms}")

    # 3. Drive match
    top_drives = [d + 1 for d in _top_n(signal_drive_scores, 3)]
    drv_overlap = len(set(expected_drives) & set(top_drives))
    if drv_overlap >= 1 or not expected_drives:
        matches += 1
    else:
        reasons.append(f"Drive mismatch: expected {expected_drives}, detected {top_drives}")

    # 4. Structural match
    structural_ok = True
    if has_descent:
        # At least two domains should be active
        active_doms = sum(1 for s in signal_domain_scores if s > 0.1)
        if active_doms < 2:
            structural_ok = False
            reasons.append("No descent pattern: fewer than 2 active domains")
    if structural_ok:
        matches += 1

    confidence = matches / 4.0
    accepted = matches >= 3

    return VerificationResult(
        accepted=accepted,
        confidence=confidence,
        matches=matches,
        total=4,
        reasons=reasons,
        detected_operators=top_ops,
        detected_domains=top_doms,
        detected_drives=top_drives,
    )
