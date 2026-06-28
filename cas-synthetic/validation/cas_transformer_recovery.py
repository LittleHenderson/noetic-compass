"""Recovery parser and fidelity scorer for CAS Transformer renderer v0.

The Phase-1 recovery parser is deterministic and intentionally narrow: it
recovers turn types from renderer-v0 templates and compares recovered trace
shape against the intended typed trace. This is the first gate for:

    intended transition -> rendered response -> recovered transition
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from cas_synthetic.schemas.cas_transformer import (
    CASTraceNode,
    CASTurnRecord,
    MetaLogicRelation,
)


RECOVERY_WEIGHTS = {
    "turn_type": 0.25,
    "cas_axis": 0.25,
    "meta_logic": 0.15,
    "trace_span": 0.15,
    "ast_equivalence": 0.10,
    "authority_surface": 0.10,
}

CRITICAL_FIELDS = ("turn_type", "compiler_valid", "trace_node_count")

_TURN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("OPEN", re.compile(r"\b(hi|i am here|ready)\b", re.IGNORECASE)),
    ("ACK", re.compile(r"\b(understood|i have the request|received)\b", re.IGNORECASE)),
    ("MIRROR", re.compile(r"\b(you are asking about|central issue|tracking the request)\b", re.IGNORECASE)),
    ("CLARIFY", re.compile(r"\b(clarify|missing constraint|trace has a gap)\b", re.IGNORECASE)),
    ("EMPATHIZE", re.compile(r"\b(sounds heavy|has weight|hear the pressure)\b", re.IGNORECASE)),
    ("REFUSE_CLAIM", re.compile(r"\b(cannot validate that claim|evidence does not support|not licensed by the trace)\b", re.IGNORECASE)),
    ("REFUSE", re.compile(r"\b(cannot do that|request crosses|have to stop)\b", re.IGNORECASE)),
    ("REPAIR", re.compile(r"\b(correction:|repair the trace|previous step was off)", re.IGNORECASE)),
    ("PLAN", re.compile(r"\b(next, we should|clean sequence|practical next move)\b", re.IGNORECASE)),
    ("CLOSE", re.compile(r"\b(completes this pass|trace is closed|stop here)\b", re.IGNORECASE)),
    ("ANSWER", re.compile(r"\b(supported answer|validated trace|cas-supported conclusion)\b", re.IGNORECASE)),
)

_AXIS_RE = re.compile(r"\^([0-9])\^?([PCEO])?(?:_\{(F[1-7])\})?\|?([TAfE])?")


@dataclass(frozen=True)
class RecoveredTraceNode:
    """Recovered trace-node approximation from rendered text."""

    node_id: str
    surface_span: str
    turn_type: str
    cas_axes: dict[str, list[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class RecoveryFidelityResult:
    """Weighted recovery-fidelity result."""

    score: float
    component_scores: dict[str, float]
    critical_exact: bool
    recovered_nodes: list[RecoveredTraceNode]
    failures: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.critical_exact and self.score >= 0.92

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 6),
            "component_scores": {
                key: round(value, 6) for key, value in self.component_scores.items()
            },
            "critical_exact": self.critical_exact,
            "passed": self.passed,
            "failures": list(self.failures),
            "recovered_nodes": [
                {
                    "node_id": node.node_id,
                    "surface_span": node.surface_span,
                    "turn_type": node.turn_type,
                    "cas_axes": dict(node.cas_axes),
                }
                for node in self.recovered_nodes
            ],
        }


class CASSurfaceRecoveryParserV0:
    """Recover renderer-v0 turn nodes from surface text."""

    parser_id = "cas_surface_recovery_parser_v0"

    def parse_record(self, record: CASTurnRecord) -> list[RecoveredTraceNode]:
        return [
            RecoveredTraceNode(
                node_id=node.node_id,
                surface_span=node.surface_span,
                turn_type=self.recover_turn_type(node.surface_span),
                cas_axes=_extract_axes(node.cas_state),
            )
            for node in record.trace
        ]

    def recover_turn_type(self, surface_span: str) -> str:
        for turn_type, pattern in _TURN_PATTERNS:
            if pattern.search(surface_span):
                return turn_type
        return "UNKNOWN"


class RecoveryFidelityScorer:
    """Score intended typed trace against recovered renderer-v0 trace."""

    def __init__(self, parser: CASSurfaceRecoveryParserV0 | None = None) -> None:
        self.parser = parser or CASSurfaceRecoveryParserV0()

    def score_record(self, record: CASTurnRecord) -> RecoveryFidelityResult:
        recovered = self.parser.parse_record(record)
        component_scores = {
            "turn_type": _turn_type_score(record.trace, recovered),
            "cas_axis": _cas_axis_score(record.trace, recovered),
            "meta_logic": _meta_logic_score(record.trace),
            "trace_span": _trace_span_score(record.trace, recovered),
            "ast_equivalence": _ast_equivalence_score(record),
            "authority_surface": _authority_surface_score(record.trace, recovered),
        }
        score = sum(
            RECOVERY_WEIGHTS[name] * component_scores[name]
            for name in RECOVERY_WEIGHTS
        )
        failures = _failures(record, recovered, component_scores)
        critical_exact = not any(
            failure.startswith(field) for field in CRITICAL_FIELDS for failure in failures
        )
        return RecoveryFidelityResult(
            score=score,
            component_scores=component_scores,
            critical_exact=critical_exact,
            recovered_nodes=recovered,
            failures=failures,
        )


def _turn_type_score(
    intended: list[CASTraceNode],
    recovered: list[RecoveredTraceNode],
) -> float:
    if not intended:
        return 0.0
    matches = sum(
        1
        for intended_node, recovered_node in zip(intended, recovered)
        if intended_node.turn_type == recovered_node.turn_type
    )
    return matches / len(intended)


def _cas_axis_score(
    intended: list[CASTraceNode],
    recovered: list[RecoveredTraceNode],
) -> float:
    if not intended:
        return 0.0
    scores: list[float] = []
    for intended_node, recovered_node in zip(intended, recovered):
        intended_axes = _extract_axes(intended_node.cas_state)
        recovered_axes = recovered_node.cas_axes
        axis_names = ("noetics", "domains", "drives", "registers")
        axis_scores = [
            _counter_jaccard(intended_axes.get(axis, []), recovered_axes.get(axis, []))
            for axis in axis_names
            if intended_axes.get(axis) or recovered_axes.get(axis)
        ]
        scores.append(sum(axis_scores) / len(axis_scores) if axis_scores else 1.0)
    return sum(scores) / len(scores)


def _meta_logic_score(intended: list[CASTraceNode]) -> float:
    if not intended:
        return 0.0
    valid = 0
    for node in intended:
        if not node.meta_logic_context.validate():
            valid += 1
    return valid / len(intended)


def _trace_span_score(
    intended: list[CASTraceNode],
    recovered: list[RecoveredTraceNode],
) -> float:
    if not intended:
        return 0.0
    if len(intended) != len(recovered):
        return 0.0
    matches = sum(
        1
        for intended_node, recovered_node in zip(intended, recovered)
        if intended_node.surface_span == recovered_node.surface_span
    )
    return matches / len(intended)


def _ast_equivalence_score(record: CASTurnRecord) -> float:
    # Phase-1 renderer v0 does not alter cas_expression. The gate verifies
    # expression trace serialization remains identical to node cas_state.
    joined = "; ".join(node.cas_state for node in record.trace)
    return 1.0 if joined == record.cas_expression else 0.0


def _authority_surface_score(
    intended: list[CASTraceNode],
    recovered: list[RecoveredTraceNode],
) -> float:
    if not intended:
        return 0.0
    scores: list[float] = []
    for intended_node, recovered_node in zip(intended, recovered):
        relations = _relations(intended_node)
        has_authority = any(relation.relation == "licenses" for relation in relations)
        is_boundary_turn = intended_node.turn_type in {"REFUSE", "REFUSE_CLAIM"}
        if has_authority or is_boundary_turn:
            scores.append(1.0 if recovered_node.turn_type == intended_node.turn_type else 0.0)
        else:
            scores.append(1.0)
    return sum(scores) / len(scores)


def _failures(
    record: CASTurnRecord,
    recovered: list[RecoveredTraceNode],
    component_scores: dict[str, float],
) -> list[str]:
    failures: list[str] = []
    if len(record.trace) != len(recovered):
        failures.append(
            f"trace_node_count: intended {len(record.trace)} recovered {len(recovered)}"
        )
    if not record.compiler.get("valid", False):
        failures.append("compiler_valid: record compiler.valid is not true")
    for intended_node, recovered_node in zip(record.trace, recovered):
        if intended_node.turn_type != recovered_node.turn_type:
            failures.append(
                "turn_type: "
                f"{intended_node.node_id} intended {intended_node.turn_type} "
                f"recovered {recovered_node.turn_type}"
            )
    for name, value in component_scores.items():
        if value < 1.0:
            failures.append(f"{name}: component score {value:.3f}")
    return failures


def _relations(node: CASTraceNode) -> list[MetaLogicRelation]:
    return list(node.meta_logic_context.relations)


def _extract_axes(cas_state: str) -> dict[str, list[str]]:
    axes = {
        "noetics": [],
        "domains": [],
        "drives": [],
        "registers": [],
    }
    for match in _AXIS_RE.finditer(cas_state):
        noetic, domain, drive, register = match.groups()
        axes["noetics"].append(f"^{noetic}")
        if domain:
            axes["domains"].append(domain)
        if drive:
            axes["drives"].append(drive)
        if register:
            axes["registers"].append(register)
    return axes


def _counter_jaccard(left: list[str], right: list[str]) -> float:
    if not left and not right:
        return 1.0
    left_counter = Counter(left)
    right_counter = Counter(right)
    intersection = sum((left_counter & right_counter).values())
    union = sum((left_counter | right_counter).values())
    return intersection / union if union else 1.0
