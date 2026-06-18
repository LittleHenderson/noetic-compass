"""B: CJT<> compiler integration + E-CJT validation passes.

Compiles a single ``CJT< cause | bias => effect >`` statement: it extracts the
embedded CAS state literals, runs them through the real CAS compiler bridge
(validity / admissibility / domain descent), and runs the node-level E-CJT
validation passes from the blueprint (Part II.5).

Relationship to ``crc_linter``: this module is the *compiler* layer (one CJT
statement, E-CJT-### codes); ``crc_linter`` is the board-level *design rule
check* (a whole circuit, CRC-### codes). They overlap deliberately, like a
language compiler's own checks vs. a separate linter.

Claim boundary: this is research compiler integration. It does NOT enable
production ``CJT<>`` authority (``is_production_cjt_syntax_enabled()`` stays
False), live trading, or broker ACCEPT.
"""

from __future__ import annotations

from enum import Enum
from typing import Iterable, Optional

from pydantic import BaseModel, Field

from cas_forex.cas_state_utils import (
    domain_rank,
    is_involution_pair,
    noetic_of,
    parse_state_literal,
)
from cas_forex.cjt_syntax import CjtSyntaxNode, parse_cjt_expression
from cas_forex.compiler_bridge import CASCompilerBridge, get_bridge
from cas_forex.schemas.cjt import CjtRegion

DEFAULT_GAIN_DIVERGENCE_LIMIT = 4.0
DEFAULT_MAX_CASCADE_DEPTH = 7


class ECjtSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


class CjtValidationFinding(BaseModel):
    code: str
    severity: ECjtSeverity
    message: str


class CjtCompilerCheck(BaseModel):
    expression: str
    terminal: str  # cause | bias | effect
    valid: bool
    is_clean: bool
    error: Optional[str] = None
    admissible: Optional[bool] = None
    domain_descent_ok: Optional[bool] = None


class CjtCompilerIntegrationReport(BaseModel):
    source_expression: str
    compiler_available: bool
    checked_expressions: list[CjtCompilerCheck] = Field(default_factory=list)
    skipped_non_state: list[str] = Field(default_factory=list)
    validation_findings: list[CjtValidationFinding] = Field(default_factory=list)
    valid: bool = False
    reason: str = ""

    @property
    def checked_count(self) -> int:
        return len(self.checked_expressions)

    @property
    def error_findings(self) -> list[CjtValidationFinding]:
        return [f for f in self.validation_findings if f.severity == ECjtSeverity.ERROR]


# ---- Node-level E-CJT validation passes ----


def validate_cjt_node(node: CjtSyntaxNode) -> list[CjtValidationFinding]:
    """Run E-CJT-001/002/003/004/006 over a single CJT node."""

    findings: list[CjtValidationFinding] = []
    bias_state = parse_state_literal(node.bias)
    cause_state = parse_state_literal(node.cause)
    effect_state = parse_state_literal(node.effect)

    # E-CJT-001 — bias must resolve to a modulating CAS state.
    if bias_state is None:
        findings.append(
            CjtValidationFinding(
                code="E-CJT-001",
                severity=ECjtSeverity.ERROR,
                message=f"MissingBiasError: bias '{node.bias}' is not a CAS state; nothing modulates cause→effect.",
            )
        )

    # E-CJT-002 — bias domain must be able to modulate the cause→effect path.
    if bias_state and cause_state and effect_state:
        b = domain_rank(bias_state.domain)
        c = domain_rank(cause_state.domain)
        e = domain_rank(effect_state.domain)
        if b is not None and c is not None and e is not None and b > c and b > e:
            findings.append(
                CjtValidationFinding(
                    code="E-CJT-002",
                    severity=ECjtSeverity.ERROR,
                    message=(
                        f"InvalidBiasDomainError: bias domain {bias_state.domain} cannot "
                        f"modulate {cause_state.domain}→{effect_state.domain} (precedence P≻C≻E≻O)."
                    ),
                )
            )

    # E-CJT-003 — declared cutoff: the CJT will not conduct.
    if node.region == CjtRegion.CUTOFF:
        findings.append(
            CjtValidationFinding(
                code="E-CJT-003",
                severity=ECjtSeverity.ERROR,
                message="CjtCutoffError: CJT declared in cutoff; cause produces no effect.",
            )
        )

    # W-CJT-004 — declared saturation warning.
    if node.region == CjtRegion.SATURATION:
        findings.append(
            CjtValidationFinding(
                code="W-CJT-004",
                severity=ECjtSeverity.WARNING,
                message="CjtSaturationWarning: CJT in saturation; further cause increase will not change effect.",
            )
        )

    # W-CJT-006 — short circuit: cause→effect skips a domain-descent tier.
    if cause_state and effect_state:
        c = domain_rank(cause_state.domain)
        e = domain_rank(effect_state.domain)
        if c is not None and e is not None and (e - c) >= 2:
            findings.append(
                CjtValidationFinding(
                    code="W-CJT-006",
                    severity=ECjtSeverity.WARNING,
                    message=(
                        f"CjtShortCircuitWarning: {cause_state.domain}→{effect_state.domain} "
                        "skips an intermediate domain (processing bypassed)."
                    ),
                )
            )

    return findings


def validate_cjt_cascade(
    nodes: list[CjtSyntaxNode],
    *,
    gain_divergence_limit: float = DEFAULT_GAIN_DIVERGENCE_LIMIT,
    max_cascade_depth: int = DEFAULT_MAX_CASCADE_DEPTH,
) -> list[CjtValidationFinding]:
    """Run cross-node passes: E-CJT-005 (push-pull) and W-CJT-007 (cascade depth)."""

    findings: list[CjtValidationFinding] = []

    # E-CJT-005 — complementary pair gain divergence.
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a, b = nodes[i], nodes[j]
            if a.cause.strip() != b.cause.strip():
                continue
            na, nb = noetic_of(a.effect), noetic_of(b.effect)
            if na is None or nb is None or not is_involution_pair(na, nb):
                continue
            if a.beta is None or b.beta is None:
                continue
            if abs(a.beta - b.beta) > gain_divergence_limit:
                findings.append(
                    CjtValidationFinding(
                        code="E-CJT-005",
                        severity=ECjtSeverity.ERROR,
                        message=(
                            f"GainDivergenceError: complementary β |{a.beta:g} − {b.beta:g}| "
                            f"exceeds limit {gain_divergence_limit:g}."
                        ),
                    )
                )

    # W-CJT-007 — cascade depth.
    adjacency: dict[int, list[int]] = {idx: [] for idx in range(len(nodes))}
    for i, a in enumerate(nodes):
        for j, b in enumerate(nodes):
            if i != j and a.effect.strip() == b.cause.strip():
                adjacency[i].append(j)
    best = {"depth": 0}

    def walk(idx: int, depth: int, visited: frozenset[int]) -> None:
        best["depth"] = max(best["depth"], depth)
        for nxt in adjacency[idx]:
            if nxt not in visited:
                walk(nxt, depth + 1, visited | {nxt})

    for start in range(len(nodes)):
        walk(start, 1, frozenset({start}))
    if best["depth"] > max_cascade_depth:
        findings.append(
            CjtValidationFinding(
                code="W-CJT-007",
                severity=ECjtSeverity.WARNING,
                message=f"CjtCascadeDepthWarning: cascade depth {best['depth']} exceeds {max_cascade_depth}.",
            )
        )
    return findings


# ---- Compiler integration ----


def compile_cjt_expression(
    expression: str,
    bridge: Optional[CASCompilerBridge] = None,
) -> CjtCompilerIntegrationReport:
    """Parse one CJT<> statement and compiler-check its embedded CAS literals."""

    node = parse_cjt_expression(expression)
    compiler = bridge or get_bridge()
    available = bool(getattr(compiler, "available", True))

    checks: list[CjtCompilerCheck] = []
    skipped: list[str] = []
    for terminal, text in (("cause", node.cause), ("bias", node.bias), ("effect", node.effect)):
        parsed = parse_state_literal(text)
        if parsed is None:
            skipped.append(f"{terminal}={text}")
            continue
        result = compiler.compile_expression(parsed.raw)
        checks.append(
            CjtCompilerCheck(
                expression=parsed.raw,
                terminal=terminal,
                valid=result.valid,
                is_clean=result.is_clean,
                error=result.error,
                admissible=result.admissible,
                domain_descent_ok=result.domain_descent_ok,
            )
        )

    findings = validate_cjt_node(node)
    has_errors = any(f.severity == ECjtSeverity.ERROR for f in findings)
    valid = bool(checks) and available and all(c.valid for c in checks) and not has_errors

    if not checks:
        reason = "No compiler-checkable CAS literals found in CJT statement."
    elif not available:
        reason = "CAS compiler not available (noetic-compass not in path)."
    elif has_errors:
        reason = "E-CJT validation reported errors."
    elif valid:
        reason = "CJT terminals compiled and validation passed."
    else:
        reason = "One or more CJT terminals failed compilation."

    return CjtCompilerIntegrationReport(
        source_expression=expression,
        compiler_available=available,
        checked_expressions=checks,
        skipped_non_state=skipped,
        validation_findings=findings,
        valid=valid,
        reason=reason,
    )


def cjt_compiler_integration_passes(expressions: Iterable[str]) -> bool:
    """Return True when every CJT statement with checkable literals compiles cleanly."""

    reports = [compile_cjt_expression(expr) for expr in expressions]
    return (
        bool(reports)
        and any(r.checked_count > 0 for r in reports)
        and all(r.valid for r in reports if r.checked_count > 0)
    )
