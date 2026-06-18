"""A-3: Cognitive Rule Check (CRC) — static design-time linter.

This is the cognitive analog of an electronics ERC/DRC (Electrical/Design Rule
Check). It inspects a circuit *specification* (CJT nodes + cross-domain vias +
fuses) and flags malformed structure BEFORE anything runs:

  - CRC-001  bias terminal does not resolve to a CAS state (unverifiable)
  - CRC-002  bias domain cannot modulate the cause→effect path
  - CRC-003  short circuit: cause→effect skips a domain-descent tier
  - CRC-004  reverse-flow bypass: feedback ascends precedence without bridging
  - CRC-005  push-pull gain divergence: |β_a − β_b| exceeds the pair limit
  - CRC-006  cascade depth exceeds the maximum stage count
  - CRC-007  gain firewall: β hypersensitive (>10) or constitution-ignoring (<0.1)
  - CRC-008  fuse installed downstream of the stage it is meant to protect

CLAIM BOUNDARY — this matters: CRC is a *static structural* check. A circuit
passing CRC is **well-formed**, NOT proven safe at runtime. "The board is
well-formed" ≠ "the AI is safe." CRC makes no runtime-safety, prompt-injection
prevention, governance, live-trading, or broker-ACCEPT claim. It only refuses to
bless malformed designs — exactly like a PCB fab rejecting a board with a short
circuit, but saying nothing about whether the manufactured device behaves well.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from cas_forex.cas_state_utils import (
    domain_of,
    domain_rank,
    is_involution_pair,
    noetic_of,
    parse_state_literal,
)
from cas_forex.cjt_syntax import CjtSyntaxNode, parse_cjt_expression

DEFAULT_GAIN_DIVERGENCE_LIMIT = 4.0
DEFAULT_MAX_CASCADE_DEPTH = 7
GAIN_HYPERSENSITIVE = 10.0
GAIN_CONSTITUTION_IGNORING = 0.1


class CrcSeverity(str, Enum):
    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"


class CrcVia(BaseModel):
    """A cross-domain interconnect (PCB via): a transition between two states."""

    source: str
    target: str


class CrcFuse(BaseModel):
    """A safety fuse installed at a stage to protect a downstream-risk stage."""

    name: str
    protects: str
    installed_at: str


class CrcCircuit(BaseModel):
    """A circuit specification to be statically checked."""

    name: str
    cjts: list[CjtSyntaxNode] = Field(default_factory=list)
    vias: list[CrcVia] = Field(default_factory=list)
    fuses: list[CrcFuse] = Field(default_factory=list)
    # Ordered stage names for power/signal sequencing (fuse placement check).
    sequence: list[str] = Field(default_factory=list)


class CrcFinding(BaseModel):
    code: str
    severity: CrcSeverity
    subject: str
    message: str
    suggestion: str = ""


class CrcReport(BaseModel):
    circuit_name: str
    findings: list[CrcFinding] = Field(default_factory=list)
    static_only: bool = True
    claim_note: str = (
        "Static structural check only. A well-formed circuit is NOT a runtime "
        "safety, prompt-injection, governance, or live-trading guarantee."
    )

    @property
    def well_formed(self) -> bool:
        """True when no ERROR-severity findings are present."""

        return not any(f.severity == CrcSeverity.ERROR for f in self.findings)

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == CrcSeverity.ERROR)

    @property
    def warn_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == CrcSeverity.WARN)


def run_crc(
    circuit: CrcCircuit,
    *,
    gain_divergence_limit: float = DEFAULT_GAIN_DIVERGENCE_LIMIT,
    max_cascade_depth: int = DEFAULT_MAX_CASCADE_DEPTH,
) -> CrcReport:
    """Run all Cognitive Rule Checks over a circuit specification."""

    findings: list[CrcFinding] = []
    for node in circuit.cjts:
        findings.extend(_check_node(node))
    findings.extend(_check_push_pull(circuit.cjts, gain_divergence_limit))
    findings.extend(_check_cascade_depth(circuit.cjts, max_cascade_depth))
    findings.extend(_check_vias(circuit.vias))
    findings.extend(_check_fuses(circuit))
    return CrcReport(circuit_name=circuit.name, findings=findings)


def run_crc_on_expressions(
    name: str,
    expressions: list[str],
    *,
    vias: Optional[list[CrcVia]] = None,
    fuses: Optional[list[CrcFuse]] = None,
    sequence: Optional[list[str]] = None,
    **kwargs,
) -> CrcReport:
    """Parse CJT<> expressions and run CRC over the resulting circuit."""

    circuit = CrcCircuit(
        name=name,
        cjts=[parse_cjt_expression(expr) for expr in expressions],
        vias=vias or [],
        fuses=fuses or [],
        sequence=sequence or [],
    )
    return run_crc(circuit, **kwargs)


# ---- Per-node checks ----


def _label(node: CjtSyntaxNode) -> str:
    return node.name or f"CJT< {node.cause} | {node.bias} => {node.effect} >"


def _check_node(node: CjtSyntaxNode) -> list[CrcFinding]:
    findings: list[CrcFinding] = []
    label = _label(node)

    cause_dom = domain_of(node.cause)
    effect_dom = domain_of(node.effect)
    bias_state = parse_state_literal(node.bias)

    # CRC-001 — bias must resolve to a CAS state to verify modulation.
    if bias_state is None:
        findings.append(
            CrcFinding(
                code="CRC-001",
                severity=CrcSeverity.WARN,
                subject=label,
                message=f"Bias '{node.bias}' is not a CAS state literal; modulation cannot be statically verified.",
                suggestion="Express the bias as a CAS state (e.g. ^5^P_{F7}|T) so its domain can be checked.",
            )
        )

    # CRC-002 — bias domain must be able to modulate the cause→effect path.
    if bias_state and cause_dom and effect_dom:
        bias_rank = domain_rank(bias_state.domain)
        cause_rank = domain_rank(cause_dom)
        effect_rank = domain_rank(effect_dom)
        if bias_rank is not None and cause_rank is not None and effect_rank is not None:
            if bias_rank > cause_rank and bias_rank > effect_rank:
                findings.append(
                    CrcFinding(
                        code="CRC-002",
                        severity=CrcSeverity.ERROR,
                        subject=label,
                        message=(
                            f"Bias domain {bias_state.domain} is lower precedence than both "
                            f"cause ({cause_dom}) and effect ({effect_dom}); it cannot modulate this path."
                        ),
                        suggestion="Use a bias in a domain of equal-or-higher precedence (P≻C≻E≻O).",
                    )
                )

    # CRC-003 / CRC-004 — descent skip vs reverse flow.
    if cause_dom and effect_dom:
        cause_rank = domain_rank(cause_dom)
        effect_rank = domain_rank(effect_dom)
        if cause_rank is not None and effect_rank is not None:
            gap = effect_rank - cause_rank
            if gap >= 2:
                findings.append(
                    CrcFinding(
                        code="CRC-003",
                        severity=CrcSeverity.ERROR,
                        subject=label,
                        message=(
                            f"Short circuit: cause {cause_dom} jumps to effect {effect_dom}, "
                            "skipping an intermediate domain tier (no evaluation step)."
                        ),
                        suggestion="Insert the intervening domain stage(s) so input is processed before output.",
                    )
                )
            elif gap < 0:
                findings.append(
                    CrcFinding(
                        code="CRC-004",
                        severity=CrcSeverity.WARN,
                        subject=label,
                        message=(
                            f"Reverse-flow bypass: effect {effect_dom} is higher precedence than "
                            f"cause {cause_dom}; feedback should route through bridging states."
                        ),
                        suggestion="Route ascending feedback through the intermediate domains rather than directly.",
                    )
                )

    # CRC-007 — gain firewall.
    if node.beta is not None:
        if node.beta > GAIN_HYPERSENSITIVE:
            findings.append(
                CrcFinding(
                    code="CRC-007",
                    severity=CrcSeverity.WARN,
                    subject=label,
                    message=f"β={node.beta:g} > {GAIN_HYPERSENSITIVE:g}: hypersensitive to framing (social-engineering exposure).",
                    suggestion="Add a feedback resistor / reduce open-loop gain.",
                )
            )
        elif 0.0 < node.beta < GAIN_CONSTITUTION_IGNORING:
            findings.append(
                CrcFinding(
                    code="CRC-007",
                    severity=CrcSeverity.WARN,
                    subject=label,
                    message=f"β={node.beta:g} < {GAIN_CONSTITUTION_IGNORING:g}: output nearly ignores its bias/constitution.",
                    suggestion="Increase bias coupling so the safety constitution can act on output.",
                )
            )

    return findings


def _check_push_pull(nodes: list[CjtSyntaxNode], limit: float) -> list[CrcFinding]:
    """CRC-005 — complementary pairs (shared cause, involution effects) must have balanced gain."""

    findings: list[CrcFinding] = []
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
            if abs(a.beta - b.beta) > limit:
                findings.append(
                    CrcFinding(
                        code="CRC-005",
                        severity=CrcSeverity.ERROR,
                        subject=f"{_label(a)} / {_label(b)}",
                        message=(
                            f"Push-pull gain divergence |{a.beta:g} − {b.beta:g}| = "
                            f"{abs(a.beta - b.beta):g} exceeds limit {limit:g}."
                        ),
                        suggestion="Balance the complementary β values so neither path dominates.",
                    )
                )
    return findings


def _check_cascade_depth(nodes: list[CjtSyntaxNode], max_depth: int) -> list[CrcFinding]:
    """CRC-006 — chained CJTs (effect→cause) must not exceed max stage depth."""

    adjacency: dict[int, list[int]] = {idx: [] for idx in range(len(nodes))}
    for i, a in enumerate(nodes):
        for j, b in enumerate(nodes):
            if i != j and a.effect.strip() == b.cause.strip():
                adjacency[i].append(j)

    best = {"depth": 0}

    def walk(idx: int, depth: int, visited: frozenset[int]) -> None:
        best["depth"] = max(best["depth"], depth)
        for nxt in adjacency[idx]:
            if nxt in visited:
                continue
            walk(nxt, depth + 1, visited | {nxt})

    for start in range(len(nodes)):
        walk(start, 1, frozenset({start}))

    if best["depth"] > max_depth:
        return [
            CrcFinding(
                code="CRC-006",
                severity=CrcSeverity.WARN,
                subject=f"cascade({best['depth']} stages)",
                message=f"CJT cascade depth {best['depth']} exceeds maximum {max_depth}.",
                suggestion="Split the cascade or insert a regulator/buffer stage.",
            )
        ]
    return []


def _check_vias(vias: list[CrcVia]) -> list[CrcFinding]:
    """CRC-004 (via form) — a via that ascends precedence without bridging."""

    findings: list[CrcFinding] = []
    for via in vias:
        src_dom = domain_of(via.source)
        tgt_dom = domain_of(via.target)
        if not src_dom or not tgt_dom:
            continue
        src_rank = domain_rank(src_dom)
        tgt_rank = domain_rank(tgt_dom)
        if src_rank is None or tgt_rank is None:
            continue
        if tgt_rank < src_rank and (src_rank - tgt_rank) >= 2:
            findings.append(
                CrcFinding(
                    code="CRC-004",
                    severity=CrcSeverity.WARN,
                    subject=f"via {via.source} → {via.target}",
                    message=(
                        f"Via ascends {src_dom}→{tgt_dom}, skipping bridging domains "
                        "(operational feedback overriding principles directly)."
                    ),
                    suggestion="Route feedback up one tier at a time (O→E→C→P).",
                )
            )
    return findings


def _check_fuses(circuit: CrcCircuit) -> list[CrcFinding]:
    """CRC-008 — a fuse must sit at or upstream of what it protects."""

    findings: list[CrcFinding] = []
    order = {name: idx for idx, name in enumerate(circuit.sequence)}
    for fuse in circuit.fuses:
        if fuse.installed_at not in order or fuse.protects not in order:
            findings.append(
                CrcFinding(
                    code="CRC-008",
                    severity=CrcSeverity.WARN,
                    subject=f"fuse {fuse.name}",
                    message=(
                        f"Fuse '{fuse.name}' references stage(s) not in the sequence "
                        f"(installed_at='{fuse.installed_at}', protects='{fuse.protects}')."
                    ),
                    suggestion="List both stages in circuit.sequence so placement can be checked.",
                )
            )
            continue
        if order[fuse.installed_at] > order[fuse.protects]:
            findings.append(
                CrcFinding(
                    code="CRC-008",
                    severity=CrcSeverity.ERROR,
                    subject=f"fuse {fuse.name}",
                    message=(
                        f"Fuse '{fuse.name}' is installed at '{fuse.installed_at}' which is "
                        f"downstream of the stage it protects ('{fuse.protects}'); it cannot trip in time."
                    ),
                    suggestion="Move the fuse upstream of the stage it protects.",
                )
            )
    return findings
