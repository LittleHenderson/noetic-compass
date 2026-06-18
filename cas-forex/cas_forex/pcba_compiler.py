"""PCBA syntax integration with the CAS compiler."""

from __future__ import annotations

import re
from typing import Any, Iterable, Optional

from pydantic import BaseModel, Field

from cas_forex.compiler_bridge import CASCompilerBridge, get_bridge
from cas_forex.pcba_syntax import PcbaComponentNode, parse_pcba_component_expression


_CAS_RELATION_RE = re.compile(
    r"\^\d+\^[A-Z](?:_\{F\d+\})?(?:\|[A-Za-z])?\s*(?:->|<->)\s*"
    r"\^\d+\^[A-Z](?:_\{F\d+\})?(?:\|[A-Za-z])?"
)
_CAS_STATE_RE = re.compile(r"\^\d+\^[A-Z](?:_\{F\d+\})?(?:\|[A-Za-z])?")
_BARE_CAS_SHORTHAND_RE = re.compile(r"(?<!\^)\^[A-Z]\b")


class PcbaCompilerCheck(BaseModel):
    expression: str
    valid: bool
    is_clean: bool
    error: Optional[str] = None
    admissible: Optional[bool] = None
    domain_descent_ok: Optional[bool] = None


class PcbaCompilerIntegrationReport(BaseModel):
    source_expression: str
    component_name: str
    compiler_available: bool
    checked_expressions: list[PcbaCompilerCheck] = Field(default_factory=list)
    skipped_shorthand: list[str] = Field(default_factory=list)
    valid: bool = False
    reason: str = ""

    @property
    def checked_count(self) -> int:
        return len(self.checked_expressions)


def compile_pcba_component_expression(
    expression: str,
    bridge: Optional[CASCompilerBridge] = None,
) -> PcbaCompilerIntegrationReport:
    """Parse one PCBA component and compiler-check embedded CAS expressions."""

    node = parse_pcba_component_expression(expression)
    return compile_pcba_component_node(node, expression, bridge=bridge)


def compile_pcba_component_node(
    node: PcbaComponentNode,
    source_expression: Optional[str] = None,
    bridge: Optional[CASCompilerBridge] = None,
) -> PcbaCompilerIntegrationReport:
    compiler = bridge or get_bridge()
    expressions = _extract_cas_expressions(node)
    checks: list[PcbaCompilerCheck] = []
    for expr in expressions:
        result = compiler.compile_expression(expr)
        checks.append(
            PcbaCompilerCheck(
                expression=expr,
                valid=result.valid,
                is_clean=result.is_clean,
                error=result.error,
                admissible=result.admissible,
                domain_descent_ok=result.domain_descent_ok,
            )
        )

    skipped = sorted(set(_extract_bare_shorthand(node)))
    valid = bool(checks) and bool(getattr(compiler, "available", True)) and all(check.valid for check in checks)
    if not checks:
        reason = "No compiler-checkable CAS expressions found in PCBA component."
    elif valid:
        reason = "Embedded CAS expressions compiled successfully."
    else:
        reason = "One or more embedded CAS expressions failed compilation."

    return PcbaCompilerIntegrationReport(
        source_expression=source_expression or node.to_expression(),
        component_name=node.component_name,
        compiler_available=bool(getattr(compiler, "available", True)),
        checked_expressions=checks,
        skipped_shorthand=skipped,
        valid=valid,
        reason=reason,
    )


def pcba_compiler_integration_passes(expressions: Iterable[str]) -> bool:
    """Return true when every compiler-checkable PCBA expression compiles."""

    reports = [compile_pcba_component_expression(expr) for expr in expressions]
    return (
        bool(reports)
        and any(report.checked_count > 0 for report in reports)
        and all(report.valid for report in reports if report.checked_count > 0)
    )


def _extract_cas_expressions(node: PcbaComponentNode) -> list[str]:
    found: list[str] = []
    for raw in _walk_values([*node.args, node.params]):
        text = str(raw)
        relation_spans: list[tuple[int, int]] = []
        for match in _CAS_RELATION_RE.finditer(text):
            found.append(_normalize_expr(match.group(0)))
            relation_spans.append(match.span())

        def inside_relation(index: int) -> bool:
            return any(start <= index < end for start, end in relation_spans)

        for match in _CAS_STATE_RE.finditer(text):
            if not inside_relation(match.start()):
                found.append(_normalize_expr(match.group(0)))
    return list(dict.fromkeys(found))


def _extract_bare_shorthand(node: PcbaComponentNode) -> list[str]:
    found: list[str] = []
    for raw in _walk_values([*node.args, node.params]):
        found.extend(match.group(0) for match in _BARE_CAS_SHORTHAND_RE.finditer(str(raw)))
    return found


def _walk_values(value: Any):
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_values(item)
    else:
        yield value


def _normalize_expr(expr: str) -> str:
    return re.sub(r"\s+", " ", expr.strip())
